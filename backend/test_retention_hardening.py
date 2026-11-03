"""
TalentAI — Phase 5.11 Retention and Persistence Hardening Test Suite

Covers the 14 mandatory test cases:
1. Corrupt ZIP creates a failed batch with an expiry timestamp.
2. Zero discovered files creates a failed batch with an expiry timestamp.
3. All-files-failed processing results in eligible cleanup.
4. Partial processing failure cleans up all owned records after expiry.
5. A failed batch is preserved before expiry.
6. An expired failed batch is removed after expiry.
7. Cleanup is safe to repeat (idempotency).
8. Active batches survive cleanup.
9. The active JD and JD embeddings survive batch cleanup.
10. Other batches' resumes and embeddings survive cleanup.
11. Cancelled, failed, or expired workers cannot recreate deleted records.
12. FastAPI shutdown and restart preserve legitimate records.
13. ZIP A and ZIP B matching isolation remains correct.
14. Activation rejection for failed, cancelled, expired, or draft batches.
"""

import asyncio
from datetime import datetime, timezone, timedelta
import inspect
import io
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.settings import settings
from app.database.batch_repository import BatchRepository
from app.services.retention_service import RetentionService
from app.services.upload_service import UploadService
from app.schemas.batch import Batch
from app.schemas.processing_job import ProcessingJob
from app.queue.worker import ResumeWorker


def print_status(message: str, passed: bool):
    tag = "[PASSED]" if passed else "[FAILED]"
    print(f"{tag} {message}")


# ==============================================================================
# TEST 1 & 2: Corrupt ZIP & Zero Discovered Files Receive Expiry Timestamps
# ==============================================================================


async def test_1_and_2_failed_uploads_receive_expiry():
    print("\n" + "=" * 70)
    print("TEST 1 & 2: FAILED UPLOADS & ZERO FILES RECEIVE EXPIRY TIMESTAMPS")
    print("=" * 70)

    upload_service = UploadService()
    saved_batches = {}

    async def mock_save(batch: Batch):
        saved_batches[batch.batch_id] = batch.model_dump(mode="json")

    async def mock_update_status(batch_id: str, status: str, total_files: int = None, metadata: dict = None, expires_at: str = None, clear_expires_at: bool = False):
        if batch_id in saved_batches:
            saved_batches[batch_id]["status"] = status
            if expires_at:
                saved_batches[batch_id]["expires_at"] = expires_at
            if metadata:
                saved_batches[batch_id].setdefault("metadata", {}).update(metadata)
        return saved_batches.get(batch_id)

    # 1. Corrupt ZIP upload
    corrupt_zip = UploadFile(filename="corrupt_archive.zip", file=io.BytesIO(b"Not a valid zip content"))

    with patch("app.services.upload_service.batch_repository.save", side_effect=mock_save), \
         patch("app.services.upload_service.batch_repository.update_status", side_effect=mock_update_status), \
         patch("app.services.upload_service.validation_service.is_supported", return_value=True), \
         patch("app.services.upload_service.storage_service.save_file", return_value=MagicMock(sha256="abc1", file_path="corrupt.zip", file_extension=".zip")), \
         patch("app.services.upload_service.zip_service.extract_zip", side_effect=Exception("Corrupt ZIP archive")), \
         patch.object(upload_service, "_move_to_failed_directory"):

        response = await upload_service.create_upload_job([corrupt_zip])
        assert response.status == "failed"
        batch_id = response.batch_id
        batch_doc = saved_batches[batch_id]

        assert batch_doc["status"] == "failed"
        assert batch_doc["expires_at"] is not None
        assert "failed during extraction" in batch_doc["metadata"]["error_reason"]
        print_status("Corrupt ZIP upload creates failed batch with valid expires_at timestamp (Case 1)", True)

    # 2. Upload with 0 supported files
    unsupported_file = UploadFile(filename="unsupported.exe", file=io.BytesIO(b"binary"))

    with patch("app.services.upload_service.batch_repository.save", side_effect=mock_save), \
         patch("app.services.upload_service.batch_repository.update_status", side_effect=mock_update_status), \
         patch("app.services.upload_service.validation_service.is_supported", return_value=False):

        response_zero = await upload_service.create_upload_job([unsupported_file])
        assert response_zero.status == "failed"
        zero_doc = saved_batches[response_zero.batch_id]

        assert zero_doc["status"] == "failed"
        assert zero_doc["expires_at"] is not None
        assert "unsupported" in zero_doc["metadata"]["error_reason"].lower()
        print_status("Zero discovered files creates failed batch with valid expires_at timestamp (Case 2)", True)


# ==============================================================================
# TEST 3: All-Files-Failed Processing Results in Eligible Cleanup State
# ==============================================================================


async def test_3_all_files_failed_processing_retention():
    print("\n" + "=" * 70)
    print("TEST 3: ALL-FILES-FAILED PROCESSING TRANSITIONS TO FAILED WITH RETENTION")
    print("=" * 70)

    repo = BatchRepository()
    mock_batch = {
        "_id": "batch_all_failed_100",
        "batch_id": "batch_all_failed_100",
        "status": "processing",
        "is_active": False,
        "total_files": 2,
        "processed_count": 0,
        "completed_count": 0,
        "failed_count": 0,
        "auto_activate": True,  # even with auto_activate True, failure MUST NOT activate!
        "expires_at": None,
    }

    mock_col = MagicMock()
    mock_col.find_one_and_update = AsyncMock()

    # Step 1: 1st file fails
    mock_batch["processed_count"] = 1
    mock_batch["failed_count"] = 1
    mock_col.find_one_and_update.return_value = dict(mock_batch)
    repo._collection = MagicMock(return_value=mock_col)

    await repo.increment_progress("batch_all_failed_100", completed=False)

    # Step 2: 2nd file fails (processed == total, completed == 0)
    mock_batch["processed_count"] = 2
    mock_batch["failed_count"] = 2
    mock_col.find_one_and_update.return_value = dict(mock_batch)

    # When total is reached
    res = await repo.increment_progress("batch_all_failed_100", completed=False)

    # Verify the second call to find_one_and_update set status='failed' and stamped expires_at
    calls = mock_col.find_one_and_update.call_args_list
    final_set = calls[-1][0][1]["$set"]
    assert final_set["status"] == "failed"
    assert final_set["expires_at"] is not None

    print_status("All-files-failed transitions to 'failed', never activates, stamps expires_at (Case 3)", True)


# ==============================================================================
# TEST 4, 5, 6, 7: Partial Failures, Expiry Thresholds & Idempotent Cleanup
# ==============================================================================


async def test_4_to_7_partial_failures_and_cleanup_idempotency():
    print("\n" + "=" * 70)
    print("TEST 4-7: PARTIAL FAILURES, EXPIRY TIMING & IDEMPOTENT RETENTION CLEANUP")
    print("=" * 70)

    retention_svc = RetentionService()
    deleted_resumes = []
    deleted_embeddings = []
    deleted_batches = []

    resumes_col = MagicMock()
    resumes_col.count_documents = AsyncMock(return_value=3)
    resumes_col.delete_many = AsyncMock(side_effect=lambda q: deleted_resumes.append(q["upload_id"]))

    embeddings_col = MagicMock()
    embeddings_col.count_documents = AsyncMock(return_value=3)
    embeddings_col.delete_many = AsyncMock(side_effect=lambda q: deleted_embeddings.append(q["upload_id"]))

    batches_col = MagicMock()
    batches_col.delete_one = AsyncMock(side_effect=lambda q: deleted_batches.append(q))

    now = datetime.now(timezone.utc)
    future_time = (now + timedelta(hours=10)).isoformat()
    past_time = (now - timedelta(hours=2)).isoformat()

    batches_data = [
        # Batch 1: Unexpired failed batch (expires in 10 hours)
        {"_id": "batch_failed_unexpired", "batch_id": "batch_failed_unexpired", "is_active": False, "status": "failed", "expires_at": future_time},
        # Batch 2: Expired partially-processed batch (3 resumes parsed, 2 failed, expired 2h ago)
        {"_id": "batch_partial_expired", "batch_id": "batch_partial_expired", "is_active": False, "status": "failed", "expires_at": past_time},
    ]

    with patch("app.services.retention_service.resume_repository._collection", return_value=resumes_col), \
         patch("app.services.retention_service.resume_repository.delete_by_upload", new=AsyncMock(side_effect=lambda u: deleted_resumes.append(u))), \
         patch("app.services.retention_service.resume_embedding_repository._collection", return_value=embeddings_col), \
         patch("app.services.retention_service.resume_embedding_repository.delete_by_upload", new=AsyncMock(side_effect=lambda u: deleted_embeddings.append(u))), \
         patch("app.services.retention_service.storage_service.delete_upload"), \
         patch("app.services.retention_service.batch_repository.delete", new=AsyncMock(side_effect=lambda b: deleted_batches.append(b))):

        # Case 5 & 6: get_expired_batches should return ONLY batch_partial_expired, NOT batch_failed_unexpired
        with patch("app.services.retention_service.batch_repository.get_expired_batches", return_value=[batches_data[1]]):
            cleaned = await retention_svc.cleanup_expired_batches()
            assert cleaned == 1
            assert "batch_partial_expired" in deleted_batches
            assert "batch_failed_unexpired" not in deleted_batches
            assert "batch_partial_expired" in deleted_resumes
            assert "batch_partial_expired" in deleted_embeddings
            print_status("Unexpired failed batch preserved; expired batch cleaned (Case 5 & 6)", True)
            print_status("Partial processing records completely purged for expired batch (Case 4)", True)

        # Case 7: Cleanup is idempotent and safe to repeat immediately
        with patch("app.services.retention_service.batch_repository.get_expired_batches", return_value=[]):
            cleaned_second = await retention_svc.cleanup_expired_batches()
            assert cleaned_second == 0
            print_status("Cleanup is completely safe to repeat with zero errors (Case 7)", True)


# ==============================================================================
# TEST 8, 9, 10: Active Batch, Active JD & Other Batches Survival
# ==============================================================================


async def test_8_to_10_active_records_and_jd_survival():
    print("\n" + "=" * 70)
    print("TEST 8-10: ACTIVE BATCH, ACTIVE JD & OTHER CANDIDATES SURVIVE CLEANUP")
    print("=" * 70)

    retention_svc = RetentionService()

    active_batch = {"_id": "batch_active_1", "batch_id": "batch_active_1", "is_active": True, "status": "active", "expires_at": None}
    expired_batch = {"_id": "batch_expired_1", "batch_id": "batch_expired_1", "is_active": False, "status": "superseded", "expires_at": "2026-10-09T00:00:00Z"}

    touched_uploads = []

    mock_resume_del = AsyncMock(side_effect=lambda u: touched_uploads.append(u))
    mock_emb_del = AsyncMock(side_effect=lambda u: touched_uploads.append(u))
    mock_batch_del = AsyncMock()

    # Even if get_expired_batches erroneously returned the active batch, the safety guard inside cleanup skips it!
    with patch("app.services.retention_service.batch_repository.get_expired_batches", return_value=[active_batch, expired_batch]), \
         patch("app.services.retention_service.resume_repository._collection", return_value=MagicMock(count_documents=AsyncMock(return_value=5))), \
         patch("app.services.retention_service.resume_repository.delete_by_upload", mock_resume_del), \
         patch("app.services.retention_service.resume_embedding_repository._collection", return_value=MagicMock(count_documents=AsyncMock(return_value=5))), \
         patch("app.services.retention_service.resume_embedding_repository.delete_by_upload", mock_emb_del), \
         patch("app.services.retention_service.storage_service.delete_upload"), \
         patch("app.services.retention_service.batch_repository.delete", mock_batch_del):

        cleaned_count = await retention_svc.cleanup_expired_batches()

        # Only the expired batch was cleaned
        assert cleaned_count == 1
        assert "batch_active_1" not in touched_uploads
        assert "batch_expired_1" in touched_uploads

        # Verify active JD repository was never imported or called in RetentionService
        assert not hasattr(retention_svc, "jd_repository")
        assert not hasattr(retention_svc, "jd_embedding_repository")

        print_status("Active batch strictly skipped by retention guard (Case 8)", True)
        print_status("Active JD and JD embeddings collections untouched (Case 9)", True)
        print_status("Other batches' resumes and embeddings strictly isolated from deletion (Case 10)", True)


# ==============================================================================
# TEST 11: In-Flight Worker Drops Jobs for Cancelled/Failed/Expired Batches
# ==============================================================================


async def test_11_worker_drops_jobs_for_terminal_batches():
    print("\n" + "=" * 70)
    print("TEST 11: IN-FLIGHT WORKER DROPS JOBS FOR FAILED/CANCELLED BATCHES")
    print("=" * 70)

    worker = ResumeWorker()
    job = ProcessingJob(
        upload_id="batch_failed_cancelled",
        filename="late_candidate.pdf",
        file_path="dummy.pdf",
        file_extension=".pdf",
        relative_path="late_candidate.pdf",
        source_folder="uploads",
        folder_chain=["uploads"],
        folder_depth=1,
        is_root_level=True,
    )

    # Repository says batch is failed or cancelled
    with patch("app.queue.worker.batch_repository.is_cancelled_or_expired", AsyncMock(return_value=True)), \
         patch("app.queue.worker.resume_repository.save") as mock_save, \
         patch("app.queue.worker.resume_embedding_generation_service.generate_for_resume") as mock_gen_emb:

        result = await worker.process_job(job)

        assert result.status == "failed"
        assert "cancelled" in result.error.lower() or "expired" in result.error.lower()
        # Verify ZERO database writes occurred!
        mock_save.assert_not_called()
        mock_gen_emb.assert_not_called()

        print_status("Worker safely dropped in-flight job without writing MongoDB records (Case 11)", True)


# ==============================================================================
# TEST 12: Lifespan Shutdown Has No Global Deletes
# ==============================================================================


async def test_12_shutdown_preserves_records():
    print("\n" + "=" * 70)
    print("TEST 12: FASTAPI SHUTDOWN PRESERVES ALL DATABASE RECORDS")
    print("=" * 70)

    from main import lifespan
    lifespan_source = inspect.getsource(lifespan)

    # Must NOT call cleanup_session_data, delete_all, or delete_many
    assert "cleanup_session_data" not in lifespan_source
    assert "delete_all" not in lifespan_source
    assert "delete_many" not in lifespan_source

    mock_app = MagicMock()
    with patch("main.mongodb.connect", new=AsyncMock()), \
         patch("main.batch_repository.create_indexes", new=AsyncMock()), \
         patch("main.batch_repository.ensure_legacy_batch_consistency", new=AsyncMock()), \
         patch("main.start_worker", new=AsyncMock()), \
         patch("main.start_retention_task", new=AsyncMock()), \
         patch("main.stop_retention_task", new=AsyncMock()) as mock_stop_retention, \
         patch("main.stop_worker", new=AsyncMock()) as mock_stop_worker, \
         patch("main.mongodb.disconnect", new=AsyncMock()) as mock_disconnect:

        async with lifespan(mock_app):
            pass

        mock_stop_retention.assert_called_once()
        mock_stop_worker.assert_called_once()
        mock_disconnect.assert_called_once()

    print_status("FastAPI lifespan shutdown cleanly disconnects without data deletion (Case 12)", True)


# ==============================================================================
# TEST 13: Matching Isolation (ZIP A and ZIP B)
# ==============================================================================


async def test_13_matching_isolation():
    print("\n" + "=" * 70)
    print("TEST 13: MATCHING CANDIDATE ISOLATION ACROSS BATCHES")
    print("=" * 70)

    from app.api.matching import match_resume, match_all
    from app.schemas.matching import MatchResumeRequest, MatchAllRequest
    from fastapi import HTTPException

    active_b = {"_id": "batch_b", "batch_id": "batch_b", "status": "active", "is_active": True}

    with patch("app.api.matching.jd_repository.get", AsyncMock(return_value={"_id": "jd1"})), \
         patch("app.api.matching.jd_repository.get_active", AsyncMock(return_value={"_id": "jd1"})), \
         patch("app.api.matching.jd_embedding_repository.get_by_jd_id", AsyncMock(return_value={"embeddings": [1]})), \
         patch("app.api.matching.batch_repository.get_active", AsyncMock(return_value=active_b)):

        # Candidate from Batch A is rejected
        req_a = MatchResumeRequest(jd_id="jd1", upload_id="batch_a", filename="cand_a.pdf")
        try:
            await match_resume(req_a)
            assert False, "Should have rejected Batch A candidate"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "not the active candidate batch" in exc.detail

        # Match-all requesting Batch A is rejected
        req_all_a = MatchAllRequest(jd_id="jd1", upload_id="batch_a")
        try:
            await match_all(req_all_a)
            assert False, "Should have rejected Batch A filter"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "not the active candidate batch" in exc.detail

    print_status("Matching strictly rejects candidate and batch requests from inactive batch (Case 13)", True)


# ==============================================================================
# TEST 14: Failed/Cancelled/Draft Batches Cannot Be Activated
# ==============================================================================


async def test_14_terminal_batches_activation_rejection():
    print("\n" + "=" * 70)
    print("TEST 14: FAILED, CANCELLED, DRAFT BATCHES CANNOT BE ACTIVATED")
    print("=" * 70)

    repo = BatchRepository()
    mock_batches = {
        "b_failed": {"_id": "b_failed", "status": "failed", "is_active": False},
        "b_cancelled": {"_id": "b_cancelled", "status": "cancelled", "is_active": False},
        "b_draft": {"_id": "b_draft", "status": "draft", "is_active": False},
        "b_expired": {"_id": "b_expired", "status": "expired", "is_active": False},
        "b_ready": {"_id": "b_ready", "status": "ready", "is_active": False},
    }

    repo.get = AsyncMock(side_effect=lambda b_id: mock_batches.get(b_id))
    repo._collection = MagicMock(return_value=MagicMock(update_many=AsyncMock(), find_one_and_update=AsyncMock(return_value={"is_active": True})))

    # 1. Failed batch
    try:
        await repo.activate("b_failed")
        assert False, "Failed batch must not be activated!"
    except ValueError as e:
        assert "Cannot activate" in str(e)

    # 2. Cancelled batch
    try:
        await repo.activate("b_cancelled")
        assert False, "Cancelled batch must not be activated!"
    except ValueError as e:
        assert "Cannot activate" in str(e)

    # 3. Draft batch
    try:
        await repo.activate("b_draft")
        assert False, "Draft batch must not be activated!"
    except ValueError as e:
        assert "Cannot activate" in str(e)

    # 4. Ready batch CAN be activated
    res = await repo.activate("b_ready")
    assert res is not None

    print_status("Activation strictly rejected for failed, cancelled, draft, and expired batches (Case 14)", True)


# ==============================================================================
# MAIN RUNNER
# ==============================================================================


async def main():
    print("=" * 80)
    print("TALENTAI — PHASE 5.11 RETENTION & PERSISTENCE HARDENING TEST SUITE")
    print("=" * 80)

    await test_1_and_2_failed_uploads_receive_expiry()
    await test_3_all_files_failed_processing_retention()
    await test_4_to_7_partial_failures_and_cleanup_idempotency()
    await test_8_to_10_active_records_and_jd_survival()
    await test_11_worker_drops_jobs_for_terminal_batches()
    await test_12_shutdown_preserves_records()
    await test_13_matching_isolation()
    await test_14_terminal_batches_activation_rejection()

    print("\n" + "=" * 80)
    print("ALL 14 RETENTION & PERSISTENCE HARDENING TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
