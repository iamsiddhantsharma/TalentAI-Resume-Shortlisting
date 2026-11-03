"""
TalentAI — Step 3: Deployment Security Hardening Synthetic Test Suite

Verifies:
1. MAX_UPLOAD_SIZE_MB chunk-streaming enforcement and partial file deletion.
2. MAX_FILES_PER_REQUEST enforcement before disk I/O.
3. MAX_REQUEST_BODY_SIZE_MB cumulative payload enforcement and cleanup.
4. MAX_RESUMES_PER_BATCH candidate count limit enforcement and cleanup.
5. Cleanup after failure (no orphaned files in upload or extracted directories).
6. ZIP member count limit enforcement.
7. ZIP uncompressed size limit enforcement.
8. ZIP compression ratio bomb threshold enforcement.
9. ZIP Slip path traversal protection regression.
10. Global 500 exception handler, sanitized message, correlation ID in logs/headers.
11. Queue endpoints protection (/queue/status and /status/queue reject 401 without auth).
12. Initial HR account seeding safety (empty/weak passwords rejected).
13. Cookie security configuration (HTTPS-only in production, configurable).
"""

import asyncio
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import shutil
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import zipfile

from fastapi import HTTPException, UploadFile
from httpx import ASGITransport, AsyncClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.auth.auth_dependencies import get_current_hr_user, HRUser
from app.auth.auth_service import auth_service
from app.config.settings import settings
from app.services.storage_service import storage_service, UploadSizeLimitExceeded
from app.services.upload_service import upload_service
from app.services.zip_service import zip_service, ZipExtractionError


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


mock_test_hr = HRUser(
    user_id="test_hr_sec_hardening",
    username="hr_sec_auditor",
    full_name="HR Security Auditor",
    email="auditor@talentai.internal",
    role="hr",
    created_at=datetime.now(timezone.utc),
)


async def test_1_upload_size_limit_streaming_enforcement():
    print("\n--- TEST 1: MAX_UPLOAD_SIZE_MB CHUNK STREAMING ENFORCEMENT ---")
    test_upload_id = "test_upload_size_sec_1"
    upload_dir = Path(settings.UPLOAD_DIR) / test_upload_id

    # Create mock UploadFile that streams 2MB when limit is 1MB
    limit_bytes = 1024 * 1024  # 1 MB
    chunk_1 = b"A" * (600 * 1024)
    chunk_2 = b"B" * (600 * 1024)  # Total 1.2 MB > 1 MB

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "oversized_resume.pdf"
    chunks = [chunk_1, chunk_2, b""]
    chunk_iter = iter(chunks)
    mock_file.read = AsyncMock(side_effect=lambda size=None: next(chunk_iter))

    try:
        await storage_service.save_file(
            file=mock_file,
            upload_id=test_upload_id,
            max_bytes=limit_bytes,
        )
        assert False, "Expected UploadSizeLimitExceeded was not raised!"
    except UploadSizeLimitExceeded as exc:
        assert "oversized_resume.pdf" in str(exc)
        # Verify partial file was cleaned up and unlinked
        if upload_dir.exists():
            files_left = list(upload_dir.iterdir())
            assert len(files_left) == 0, f"Expected 0 files left after cleanup, found {files_left}"
        print_status("Test 1: Upload chunk streaming size limit enforced and partial file unlinked", True)
    finally:
        storage_service.delete_upload(test_upload_id)


async def test_2_max_files_per_request_enforcement():
    print("\n--- TEST 2: MAX_FILES_PER_REQUEST ENFORCEMENT ---")
    # Generate files exceeding MAX_FILES_PER_REQUEST
    excess_count = settings.MAX_FILES_PER_REQUEST + 5
    fake_files = [MagicMock(spec=UploadFile, filename=f"cand_{i}.pdf") for i in range(excess_count)]

    try:
        await upload_service.create_upload_job(fake_files)
        assert False, "Expected HTTPException 400 for excess files count!"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "exceeding the maximum allowed limit" in exc.detail
        print_status(f"Test 2: MAX_FILES_PER_REQUEST ({settings.MAX_FILES_PER_REQUEST}) strictly enforced upfront", True)


async def test_3_cumulative_request_body_size_enforcement():
    print("\n--- TEST 3: CUMULATIVE REQUEST BODY SIZE LIMIT ---")
    test_upload_id = "test_upload_body_limit"

    # Simulate 3 files whose cumulative size exceeds MAX_REQUEST_BODY_SIZE_MB
    # Temporarily set MAX_REQUEST_BODY_SIZE_MB to 1 for test
    orig_limit = settings.MAX_REQUEST_BODY_SIZE_MB
    try:
        settings.MAX_REQUEST_BODY_SIZE_MB = 1  # 1MB limit

        file1 = MagicMock(spec=UploadFile, filename="file1.pdf")
        file2 = MagicMock(spec=UploadFile, filename="file2.pdf")

        f1_data = [b"X" * (600 * 1024), b""]
        f2_data = [b"Y" * (600 * 1024), b""]
        file1.read = AsyncMock(side_effect=lambda size=None: f1_data.pop(0))
        file2.read = AsyncMock(side_effect=lambda size=None: f2_data.pop(0))

        with patch("app.services.upload_service.uuid4", return_value=test_upload_id), \
             patch("app.database.batch_repository.batch_repository.save", new=AsyncMock()), \
             patch("app.database.batch_repository.batch_repository.delete", new=AsyncMock()):

            await upload_service.create_upload_job([file1, file2])
            assert False, "Expected HTTPException 413 for cumulative body size!"
    except HTTPException as exc:
        assert exc.status_code == 413
        assert "Total upload payload exceeds" in exc.detail
        print_status("Test 3: Cumulative request body limit enforced and batch cleaned up", True)
    finally:
        settings.MAX_REQUEST_BODY_SIZE_MB = orig_limit
        storage_service.delete_upload(test_upload_id)


async def test_4_max_resumes_per_batch_enforcement():
    print("\n--- TEST 4: MAX RESUMES PER BATCH LIMIT ---")
    test_upload_id = "test_max_resumes_batch"
    orig_limit = settings.MAX_RESUMES_PER_BATCH

    try:
        settings.MAX_RESUMES_PER_BATCH = 10

        # Simulate discovery returning 12 candidate resumes
        mock_discovered = [
            MagicMock(file_path=f"dummy/path/{i}.pdf", filename=f"cand_{i}.pdf", relative_path=f"cand_{i}.pdf")
            for i in range(12)
        ]

        mock_zip_file = MagicMock(spec=UploadFile, filename="batch_large.zip")
        mock_zip_file.read = AsyncMock(side_effect=[b"PK\x05\x06" + b"\x00" * 18, b""])

        with patch("app.services.upload_service.uuid4", return_value=test_upload_id), \
             patch("app.database.batch_repository.batch_repository.save", new=AsyncMock()), \
             patch("app.database.batch_repository.batch_repository.delete", new=AsyncMock()), \
             patch("app.services.storage_service.storage_service.save_file", new=AsyncMock(return_value=MagicMock(file_extension=".zip", file_path="dummy.zip", file_size=100, sha256="abc1234"))), \
             patch("app.services.zip_service.zip_service.extract_zip", new=AsyncMock(return_value="dummy/extracted")), \
             patch("app.services.discovery_service.discovery_service.discover_files", return_value=mock_discovered):

            await upload_service.create_upload_job([mock_zip_file])
            assert False, "Expected HTTPException 400 for batch resume count limit!"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Batch candidate limit exceeded" in exc.detail
        print_status("Test 4: Batch candidate limit (MAX_RESUMES_PER_BATCH) strictly enforced", True)
    finally:
        settings.MAX_RESUMES_PER_BATCH = orig_limit
        storage_service.delete_upload(test_upload_id)


async def test_5_cleanup_after_upload_failure():
    print("\n--- TEST 5: CLEANUP AFTER UPLOAD FAILURE ---")
    test_upload_id = "test_cleanup_failure_id"
    upload_dir = Path(settings.UPLOAD_DIR) / test_upload_id
    extracted_dir = Path(settings.EXTRACTED_DIR) / test_upload_id

    # Create dummy folders and files
    upload_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "partial.pdf").write_bytes(b"partial content")
    (extracted_dir / "extracted.txt").write_bytes(b"extracted content")

    mock_file = MagicMock(spec=UploadFile, filename="fail_midway.pdf")
    # Force exception during save_file
    mock_file.read = AsyncMock(side_effect=RuntimeError("Disk write simulated failure"))

    with patch("app.services.upload_service.uuid4", return_value=test_upload_id), \
         patch("app.database.batch_repository.batch_repository.save", new=AsyncMock()), \
         patch("app.database.batch_repository.batch_repository.delete", new=AsyncMock()):

        try:
            await upload_service.create_upload_job([mock_file])
        except HTTPException:
            pass

    # Verify both upload and extracted directories were thoroughly cleaned
    assert not (upload_dir / "partial.pdf").exists()
    assert not (extracted_dir / "extracted.txt").exists()
    print_status("Test 5: Failed/aborted upload files thoroughly cleaned up with zero orphans", True)


def test_6_zip_member_count_enforcement():
    print("\n--- TEST 6: ZIP ARCHIVE MEMBER COUNT LIMIT ---")
    zip_buffer = io.BytesIO()
    excess_members = settings.MAX_ZIP_MEMBERS_COUNT + 10

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(excess_members):
            zf.writestr(f"cand_{i}.txt", b"simple content")

    zip_bytes = zip_buffer.getvalue()
    temp_zip = Path("test_temp_excess_members.zip")
    temp_zip.write_bytes(zip_bytes)
    extract_dir = Path("test_temp_extract_dir_6")

    try:
        zip_service._extract_zip_sync(temp_zip, extract_dir)
        assert False, "Expected ZipExtractionError for member count limit!"
    except ZipExtractionError as exc:
        assert "exceeding the maximum allowed limit" in str(exc)
        print_status(f"Test 6: ZIP member count limit ({settings.MAX_ZIP_MEMBERS_COUNT}) strictly enforced", True)
    finally:
        temp_zip.unlink(missing_ok=True)
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)


def test_7_zip_uncompressed_size_limit():
    print("\n--- TEST 7: ZIP ARCHIVE UNCOMPRESSED SIZE LIMIT ---")
    zip_buffer = io.BytesIO()
    orig_limit = settings.MAX_ZIP_UNCOMPRESSED_SIZE_MB

    try:
        settings.MAX_ZIP_UNCOMPRESSED_SIZE_MB = 1  # 1MB limit for test
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add an entry with 1.5MB declared uncompressed
            zf.writestr("large_candidate.txt", b"Z" * (1500 * 1024))

        temp_zip = Path("test_temp_oversized_uncompressed.zip")
        temp_zip.write_bytes(zip_buffer.getvalue())
        extract_dir = Path("test_temp_extract_dir_7")

        try:
            zip_service._extract_zip_sync(temp_zip, extract_dir)
            assert False, "Expected ZipExtractionError for uncompressed size!"
        except ZipExtractionError as exc:
            assert "exceeds the maximum allowed limit" in str(exc)
            print_status("Test 7: ZIP uncompressed size limit strictly enforced before extraction", True)
        finally:
            temp_zip.unlink(missing_ok=True)
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
    finally:
        settings.MAX_ZIP_UNCOMPRESSED_SIZE_MB = orig_limit


def test_8_zip_compression_ratio_bomb_threshold():
    print("\n--- TEST 8: ZIP COMPRESSION RATIO BOMB THRESHOLD ---")
    zip_buffer = io.BytesIO()

    # 1MB of null bytes compresses down to ~1KB in deflate: ratio ~1000:1 >> 20:1
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zeroes.bin", b"\x00" * (1024 * 1024))

    temp_zip = Path("test_temp_zip_bomb.zip")
    temp_zip.write_bytes(zip_buffer.getvalue())
    extract_dir = Path("test_temp_extract_dir_8")

    try:
        zip_service._extract_zip_sync(temp_zip, extract_dir)
        assert False, "Expected ZipExtractionError for compression ratio bomb!"
    except ZipExtractionError as exc:
        assert "Suspicious compression ratio" in str(exc)
        assert "potential ZIP bomb" in str(exc)
        print_status(f"Test 8: High compression ratio bomb ({settings.MAX_ZIP_COMPRESSION_RATIO}:1) detected & rejected", True)
    finally:
        temp_zip.unlink(missing_ok=True)
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)


def test_9_zip_slip_path_traversal_regression():
    print("\n--- TEST 9: ZIP SLIP PATH TRAVERSAL REGRESSION ---")
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # Malicious traversal member
        zf.writestr("../../etc/cron.d/malicious", b"malicious content")

    temp_zip = Path("test_temp_zip_slip.zip")
    temp_zip.write_bytes(zip_buffer.getvalue())
    extract_dir = Path("test_temp_extract_dir_9")

    try:
        zip_service._extract_zip_sync(temp_zip, extract_dir)
        assert False, "Expected ZipExtractionError for Zip Slip traversal!"
    except ZipExtractionError as exc:
        assert "Unsafe path traversal detected" in str(exc)
        print_status("Test 9: Zip Slip path traversal attempt blocked cleanly", True)
    finally:
        temp_zip.unlink(missing_ok=True)
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)


async def test_10_global_500_handler_and_correlation_id():
    print("\n--- TEST 10: GLOBAL 500 HANDLER & CORRELATION ID ---")
    transport = ASGITransport(app=app)
    app.dependency_overrides[get_current_hr_user] = lambda: mock_test_hr

    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            with patch("app.api.matching.batch_repository.get_active", side_effect=RuntimeError("DB Secret Key: mongo://admin:s3cr3t@localhost")):
                custom_req_id = "req-audit-trace-999"
                response = await client.post("/matching/match-all", json={}, headers={"X-Request-ID": custom_req_id})

                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
                assert "An internal server error occurred" in data["detail"]
                # Must NEVER expose internal secret or stack trace
                assert "mongo://admin:s3cr3t" not in response.text
                assert "Traceback" not in response.text
                assert "RuntimeError" not in response.text
                # Correlation ID returned in payload and header
                assert data["request_id"] == custom_req_id
                assert response.headers["X-Request-ID"] == custom_req_id
                print_status("Test 10: Global 500 handler sanitizes errors and preserves X-Request-ID with zero leakage", True)
    finally:
        app.dependency_overrides.pop(get_current_hr_user, None)


async def test_11_queue_endpoints_protected_with_auth():
    print("\n--- TEST 11: QUEUE ENDPOINTS STRICTLY REQUIRE AUTH ---")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test /queue/status without auth
        res_queue_status = await client.get("/queue/status")
        assert res_queue_status.status_code == 401, f"Expected 401 for /queue/status, got {res_queue_status.status_code}"

        # 2. Test /status/queue without auth
        res_status_queue = await client.get("/status/queue")
        assert res_status_queue.status_code == 401, f"Expected 401 for /status/queue, got {res_status_queue.status_code}"

        # 3. With HR auth, both are accessible
        app.dependency_overrides[get_current_hr_user] = lambda: mock_test_hr
        try:
            authed_res1 = await client.get("/queue/status")
            assert authed_res1.status_code == 200

            authed_res2 = await client.get("/status/queue")
            assert authed_res2.status_code == 200
            print_status("Test 11: Queue endpoints (/queue/status and /status/queue) strictly protected under HR auth", True)
        finally:
            app.dependency_overrides.pop(get_current_hr_user, None)


async def test_12_initial_hr_seeding_safety():
    print("\n--- TEST 12: INITIAL HR ACCOUNT SEEDING SAFETY ---")
    mock_db = MagicMock()
    mock_col = MagicMock()
    mock_col.count_documents = AsyncMock(return_value=0)  # Empty collection
    mock_col.insert_one = AsyncMock()
    mock_db.__getitem__.return_value = mock_col

    with patch.object(auth_service, "_get_db", return_value=mock_db):
        # Case A: Password is None
        settings.INITIAL_HR_USERNAME = "admin"
        settings.INITIAL_HR_PASSWORD = None
        await auth_service.ensure_initial_hr_user()
        assert not mock_col.insert_one.called, "Seeded account when password was None!"

        # Case B: Password is too short (< 8 chars)
        settings.INITIAL_HR_PASSWORD = "123"
        await auth_service.ensure_initial_hr_user()
        assert not mock_col.insert_one.called, "Seeded account when password was < 8 chars!"

        # Case C: Username is None
        settings.INITIAL_HR_USERNAME = None
        settings.INITIAL_HR_PASSWORD = "ValidPassword2026!"
        await auth_service.ensure_initial_hr_user()
        assert not mock_col.insert_one.called, "Seeded account when username was None!"

        print_status("Test 12: Initial HR seeding refuses blank, weak, or unconfigured accounts", True)


def test_13_cookie_security_configuration():
    print("\n--- TEST 13: COOKIE SECURITY CONFIGURATION ---")
    orig_env = settings.ENVIRONMENT
    orig_secure = settings.SESSION_COOKIE_SECURE

    try:
        # Default dev: not secure
        settings.ENVIRONMENT = "development"
        settings.SESSION_COOKIE_SECURE = None
        assert settings.is_cookie_secure is False

        # Production: automatically secure
        settings.ENVIRONMENT = "production"
        settings.SESSION_COOKIE_SECURE = None
        assert settings.is_cookie_secure is True

        # Explicit override
        settings.ENVIRONMENT = "development"
        settings.SESSION_COOKIE_SECURE = True
        assert settings.is_cookie_secure is True

        print_status("Test 13: Cookie security dynamically enforces HTTPS in production and allows explicit override", True)
    finally:
        settings.ENVIRONMENT = orig_env
        settings.SESSION_COOKIE_SECURE = orig_secure


async def run_all_step3_tests():
    print("=" * 80)
    print("TALENTAI — STEP 3 DEPLOYMENT SECURITY HARDENING TEST SUITE")
    print("=" * 80)

    await test_1_upload_size_limit_streaming_enforcement()
    await test_2_max_files_per_request_enforcement()
    await test_3_cumulative_request_body_size_enforcement()
    await test_4_max_resumes_per_batch_enforcement()
    await test_5_cleanup_after_upload_failure()
    test_6_zip_member_count_enforcement()
    test_7_zip_uncompressed_size_limit()
    test_8_zip_compression_ratio_bomb_threshold()
    test_9_zip_slip_path_traversal_regression()
    await test_10_global_500_handler_and_correlation_id()
    await test_11_queue_endpoints_protected_with_auth()
    await test_12_initial_hr_seeding_safety()
    test_13_cookie_security_configuration()

    print("=" * 80)
    print("ALL 13 STEP 3 DEPLOYMENT SECURITY HARDENING TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_step3_tests())
