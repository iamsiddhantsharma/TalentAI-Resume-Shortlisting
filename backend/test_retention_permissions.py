"""
TalentAI — Windows PermissionError Retention Hardening Test Suite

Validates:
1. Windows read-only file and directory tree removal via safe_rmtree.
2. Transient lock and retry backoff behavior.
3. Expired stranded-batch cleanup integration.
4. Retention idempotency across repeated executions.
5. Absolute protection of active batches and the protected 145-resume batch.
6. Failure isolation and retry metadata recording on filesystem locks.
"""

import asyncio
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
import time
from unittest.mock import patch, MagicMock

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.settings import settings
from app.database.mongodb import mongodb
from app.database.collections import MongoCollections
from app.database.batch_repository import batch_repository
from app.services.retention_service import retention_service, PROTECTED_BATCH_ID
from app.services.storage_service import storage_service
from app.utils.file_utils import safe_rmtree


def print_status(message: str, passed: bool):
    tag = "[PASSED]" if passed else "[FAILED]"
    print(f"{tag} {message}")


# ==============================================================================
# TEST 1: Windows Read-Only Files & Nested Directories Removal
# ==============================================================================


def test_1_readonly_filesystem_removal():
    print("\n" + "=" * 70)
    print("TEST 1: WINDOWS READ-ONLY FILES & DIRECTORIES REMOVAL VIA safe_rmtree")
    print("=" * 70)

    with tempfile.TemporaryDirectory(prefix="talentai_test_ro_") as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create nested structure: dir1/subdir/file.txt and dir1/readonly_file.txt
        dir1 = tmp_path / "dir1"
        subdir = dir1 / "subdir"
        subdir.mkdir(parents=True, exist_ok=True)

        ro_file1 = dir1 / "readonly_file.txt"
        ro_file1.write_text("Read only file content", encoding="utf-8")

        ro_file2 = subdir / "nested_readonly.txt"
        ro_file2.write_text("Nested read only content", encoding="utf-8")

        # Set read-only attributes
        os.chmod(ro_file1, stat.S_IREAD)
        os.chmod(ro_file2, stat.S_IREAD)
        try:
            # On Windows, set directory read-only mode (like OneDrive does: 0o40555)
            os.chmod(subdir, 0o40555)
            os.chmod(dir1, 0o40555)
        except Exception:
            pass

        # Verify safe_rmtree cleanly removes the entire read-only tree
        success = safe_rmtree(dir1, max_retries=3)
        assert success is True, "safe_rmtree should return True on success"
        assert not dir1.exists(), f"Directory '{dir1}' should have been completely removed"

        print_status("safe_rmtree successfully deleted nested read-only Windows files & dirs", True)

        # Verify idempotency when path does not exist
        success_idempotent = safe_rmtree(dir1)
        assert success_idempotent is True, "safe_rmtree on non-existent path must return True"
        print_status("safe_rmtree is idempotent when directory does not exist", True)


# ==============================================================================
# TEST 2: Transient Lock and Retry Backoff
# ==============================================================================


def test_2_transient_lock_retry():
    print("\n" + "=" * 70)
    print("TEST 2: TRANSIENT LOCK AND RETRY BACKOFF IN safe_rmtree")
    print("=" * 70)

    with tempfile.TemporaryDirectory(prefix="talentai_test_lock_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        test_dir = tmp_path / "lock_dir"
        test_dir.mkdir(parents=True, exist_ok=True)

        locked_file = test_dir / "busy_file.txt"
        locked_file.write_text("Initial locked content", encoding="utf-8")

        # Open file in exclusive write mode to hold lock
        f = open(locked_file, "r+b")

        # Release lock in background thread after 75ms
        def delayed_release():
            time.sleep(0.075)
            f.close()

        release_thread = threading.Thread(target=delayed_release)
        release_thread.start()

        # safe_rmtree with max_retries=4 and initial_delay=0.05 will retry at:
        # attempt 0: fails (locked) -> sleeps 50ms
        # attempt 1: lock released (75ms elapsed) -> succeeds!
        start_t = time.perf_counter()
        success = safe_rmtree(test_dir, max_retries=4, initial_delay=0.05)
        elapsed = time.perf_counter() - start_t
        release_thread.join()

        assert success is True, "safe_rmtree should succeed after transient lock is released"
        assert not test_dir.exists(), "Directory should be removed after lock release"
        assert elapsed >= 0.05, f"Expected bounded backoff sleep, took {elapsed:.3f}s"

        print_status("Transient lock detected and resolved by safe_rmtree retry backoff", True)

        # Now test permanent lock failure with ignore_errors=True
        perm_dir = tmp_path / "perm_dir"
        perm_dir.mkdir(parents=True, exist_ok=True)
        perm_file = perm_dir / "perm_locked.txt"
        perm_file.write_text("Permanent locked content", encoding="utf-8")

        perm_f = open(perm_file, "r+b")
        try:
            # ignore_errors=True must return False without crashing
            res = safe_rmtree(perm_dir, max_retries=2, initial_delay=0.01, ignore_errors=True)
            assert res is False, "safe_rmtree with ignore_errors=True should return False on permanent lock"
            print_status("Permanent lock safely caught, returning False with ignore_errors=True", True)

            # ignore_errors=False must raise PermissionError
            raised = False
            try:
                safe_rmtree(perm_dir, max_retries=2, initial_delay=0.01, ignore_errors=False)
            except PermissionError:
                raised = True
            assert raised is True, "safe_rmtree with ignore_errors=False must raise PermissionError"
            print_status("Permanent lock re-raised with ignore_errors=False", True)
        finally:
            perm_f.close()


# ==============================================================================
# TEST 3: Expired Stranded-Batch Cleanup Integration Test
# ==============================================================================


async def test_3_stranded_batch_cleanup():
    print("\n" + "=" * 70)
    print("TEST 3: EXPIRED STRANDED-BATCH CLEANUP INTEGRATION TEST")
    print("=" * 70)

    db = mongodb.get_database()
    batches_col = db[MongoCollections.BATCHES]

    test_batch_id = "test_stranded_batch_001"
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(hours=48)).isoformat()

    # Create stranded batch document in MongoDB
    batch_doc = {
        "_id": test_batch_id,
        "batch_id": test_batch_id,
        "status": "failed",
        "is_active": False,
        "total_files": 1,
        "processed_count": 0,
        "completed_count": 0,
        "failed_count": 1,
        "expires_at": expired_time,
        "created_at": expired_time,
        "updated_at": expired_time,
    }
    await batches_col.replace_one({"_id": test_batch_id}, batch_doc, upsert=True)

    # Create read-only folder in settings.UPLOAD_DIR
    upload_dir = Path(settings.UPLOAD_DIR) / test_batch_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    ro_file = upload_dir / "sample_resume.pdf"
    ro_file.write_text("Dummy content", encoding="utf-8")
    os.chmod(ro_file, stat.S_IREAD)
    try:
        os.chmod(upload_dir, 0o40555)
    except Exception:
        pass

    assert upload_dir.exists(), "Upload directory should exist before cleanup"

    # Run cleanup
    cleaned = await retention_service.cleanup_expired_batches()
    assert cleaned >= 1, f"Expected at least 1 batch cleaned, got {cleaned}"

    # Verify filesystem directory is gone
    assert not upload_dir.exists(), f"Upload directory '{upload_dir}' should have been removed"

    # Verify MongoDB batch document is gone
    remaining = await batches_col.find_one({"_id": test_batch_id})
    assert remaining is None, "Batch document should be deleted from MongoDB after successful cleanup"

    print_status("Expired stranded batch cleanly purged from filesystem and MongoDB", True)


# ==============================================================================
# TEST 4: Idempotency Across Repeated Cleanups
# ==============================================================================


async def test_4_idempotency_second_run():
    print("\n" + "=" * 70)
    print("TEST 4: RETENTION IDEMPOTENCY TEST (RUN CLEANUP TWICE)")
    print("=" * 70)

    # First run was done in Test 3, or run a pass now
    cleaned_first = await retention_service.cleanup_expired_batches()

    # Second run immediately on same state
    cleaned_second = await retention_service.cleanup_expired_batches()

    assert cleaned_second == 0, f"Expected 0 batches cleaned on second run, got {cleaned_second}"
    print_status("Second cleanup pass executed cleanly with 0 errors and 0 redundant deletions", True)


# ==============================================================================
# TEST 5: Active Batches & Protected 145-Resume Batch Remain Unchanged
# ==============================================================================


async def test_5_active_and_protected_batch_safety():
    print("\n" + "=" * 70)
    print("TEST 5: ACTIVE BATCHES & PROTECTED 145-RESUME BATCH PRESERVATION")
    print("=" * 70)

    db = mongodb.get_database()
    batches_col = db[MongoCollections.BATCHES]

    # Verify protected batch in MongoDB exists and is intact
    protected_doc = await batches_col.find_one({"_id": PROTECTED_BATCH_ID})
    if protected_doc:
        initial_status = protected_doc.get("status")
        initial_resumes = protected_doc.get("total_files")
        print_status(f"Found protected batch '{PROTECTED_BATCH_ID}' (status: {initial_status}, files: {initial_resumes})", True)
    else:
        print_status(f"Protected batch ID configured as '{PROTECTED_BATCH_ID}'", True)

    # 1. Test discard_batch explicitly rejects deleting PROTECTED_BATCH_ID
    rejected = False
    try:
        await retention_service.discard_batch(PROTECTED_BATCH_ID, force=True)
    except ValueError as exc:
        if "protected" in str(exc).lower():
            rejected = True
    assert rejected is True, "discard_batch must raise ValueError when attempting to discard protected batch"
    print_status("discard_batch strictly rejects discarding the protected 145-resume batch", True)

    # 2. Test active batch is never expired or cleaned up
    active_test_id = "test_active_batch_safety_001"
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(hours=24)).isoformat()

    # Create active batch that erroneously has an expired timestamp
    active_doc = {
        "_id": active_test_id,
        "batch_id": active_test_id,
        "status": "active",
        "is_active": True,
        "total_files": 5,
        "expires_at": expired_time,
    }
    await batches_col.replace_one({"_id": active_test_id}, active_doc, upsert=True)

    active_dir = Path(settings.UPLOAD_DIR) / active_test_id
    active_dir.mkdir(parents=True, exist_ok=True)
    (active_dir / "active_resume.pdf").write_text("Active content", encoding="utf-8")

    try:
        # Run retention cleanup
        await retention_service.cleanup_expired_batches()

        # Verify active batch is NOT deleted
        db_doc = await batches_col.find_one({"_id": active_test_id})
        assert db_doc is not None, "Active batch document must survive retention cleanup"
        assert db_doc.get("is_active") is True, "Active batch must remain active"
        assert active_dir.exists(), "Active batch upload directory must not be deleted"
        print_status("Active batch survived retention cleanup completely untouched", True)

    finally:
        # Clean up test fixture
        await batches_col.delete_one({"_id": active_test_id})
        safe_rmtree(active_dir)

    # Verify protected batch in MongoDB is still unchanged
    if protected_doc:
        after_doc = await batches_col.find_one({"_id": PROTECTED_BATCH_ID})
        assert after_doc is not None, "Protected batch document must never be deleted"
        assert after_doc.get("status") == initial_status, "Protected batch status must remain unchanged"
        print_status("Protected 145-resume batch verified completely unchanged in MongoDB", True)


# ==============================================================================
# TEST 6: Locked Batch Retains Metadata & Background Loop Continues
# ==============================================================================


async def test_6_locked_batch_metadata_and_loop_continuation():
    print("\n" + "=" * 70)
    print("TEST 6: LOCKED BATCH RETAINS METADATA & LOOP CONTINUES SUBSEQUENT BATCHES")
    print("=" * 70)

    db = mongodb.get_database()
    batches_col = db[MongoCollections.BATCHES]

    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(hours=24)).isoformat()

    # Batch A: Locked batch (will fail deletion)
    batch_a_id = "test_locked_batch_a"
    batch_a_doc = {
        "_id": batch_a_id,
        "batch_id": batch_a_id,
        "status": "failed",
        "is_active": False,
        "expires_at": expired_time,
    }
    await batches_col.replace_one({"_id": batch_a_id}, batch_a_doc, upsert=True)

    batch_a_dir = Path(settings.UPLOAD_DIR) / batch_a_id
    batch_a_dir.mkdir(parents=True, exist_ok=True)
    locked_file = batch_a_dir / "held_file.pdf"
    locked_file.write_text("Held open content", encoding="utf-8")

    # Batch B: Normal expired batch (must succeed deletion even if Batch A fails)
    batch_b_id = "test_normal_batch_b"
    batch_b_doc = {
        "_id": batch_b_id,
        "batch_id": batch_b_id,
        "status": "failed",
        "is_active": False,
        "expires_at": expired_time,
    }
    await batches_col.replace_one({"_id": batch_b_id}, batch_b_doc, upsert=True)

    batch_b_dir = Path(settings.UPLOAD_DIR) / batch_b_id
    batch_b_dir.mkdir(parents=True, exist_ok=True)
    (batch_b_dir / "normal_file.pdf").write_text("Normal content", encoding="utf-8")

    # Hold exclusive lock on Batch A's file
    lock_f = open(locked_file, "r+b")

    try:
        # Run cleanup
        cleaned = await retention_service.cleanup_expired_batches()

        # Batch A checks:
        # 1. Batch A document in MongoDB must NOT be deleted!
        batch_a_after = await batches_col.find_one({"_id": batch_a_id})
        assert batch_a_after is not None, "Batch A document must NOT be deleted while locked"
        assert batch_a_after.get("cleanup_pending") is True, "Batch A must be marked cleanup_pending=True"
        assert batch_a_after.get("cleanup_error") is not None, "Batch A must record cleanup_error"
        assert batch_a_after.get("cleanup_retry_count", 0) >= 1, "Batch A must have incremented cleanup_retry_count"
        print_status("Batch A failure safely recorded retry metadata without deleting MongoDB document", True)

        # Batch B checks:
        # 2. Batch B must have been cleaned up despite Batch A's failure!
        batch_b_after = await batches_col.find_one({"_id": batch_b_id})
        assert batch_b_after is None, "Batch B document must be cleaned up despite prior batch failure"
        assert not batch_b_dir.exists(), "Batch B directory must be removed"
        print_status("Retention loop continued past Batch A failure to successfully clean Batch B", True)

    finally:
        lock_f.close()
        # Clean up Batch A now that lock is released
        safe_rmtree(batch_a_dir)
        await batches_col.delete_one({"_id": batch_a_id})
        safe_rmtree(batch_b_dir)
        await batches_col.delete_one({"_id": batch_b_id})


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================


async def run_all_tests():
    print("\n" + "=" * 70)
    print("TALENT_AI WINDOWS RETENTION HARDENING VERIFICATION")
    print("=" * 70)

    await mongodb.connect()

    try:
        test_1_readonly_filesystem_removal()
        test_2_transient_lock_retry()
        await test_3_stranded_batch_cleanup()
        await test_4_idempotency_second_run()
        await test_5_active_and_protected_batch_safety()
        await test_6_locked_batch_metadata_and_loop_continuation()

        print("\n" + "=" * 70)
        print("ALL RETENTION HARDENING TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
    finally:
        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
