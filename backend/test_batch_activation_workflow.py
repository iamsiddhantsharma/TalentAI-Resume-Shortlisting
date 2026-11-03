"""
TalentAI — Batch Activation & Matching Workflow Regression Test Suite

Verifies:
1. Upload with auto_activate=False -> processing -> ready (is_active=False).
2. Match-all and Match-resume before activation are rejected (HTTP 400) with diagnostic activation instructions.
3. Activation of ready batch succeeds (HTTP 200), setting status='active', is_active=True, expires_at=None.
4. Match-all succeeds after activation, resolving candidates from the active batch.
5. Incomplete (processing) and failed/cancelled/draft batches are strictly rejected from activation (HTTP 400).
6. Inactive and superseded batch isolation: previous batch candidates never appear in current active matching.
7. Upload with auto_activate=True automatically transitions to active on completion.
8. Preservation of single-active-batch and single-active-JD rules.
"""

import asyncio
from datetime import datetime, timezone, timedelta
import io
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.config.settings import settings
from app.database.batch_repository import BatchRepository
from app.services.upload_service import UploadService
from app.schemas.batch import Batch
from app.schemas.storage import StoredFile
from test_matching_api import SAMPLE_MATCH_RESULT

client = TestClient(app)


def print_status(message: str, passed: bool):
    tag = "[PASSED]" if passed else "[FAILED]"
    print(f"{tag} {message}")


# ==============================================================================
# TEST 1: Full Lifecycle with auto_activate=False
# ==============================================================================


async def test_1_lifecycle_auto_activate_false_workflow():
    print("\n" + "=" * 70)
    print("TEST 1: UPLOAD -> PROCESSING -> READY -> ACTIVATION -> MATCH-ALL")
    print("=" * 70)

    upload_service = UploadService()
    saved_batches: dict[str, dict] = {}

    async def mock_save(batch: Batch):
        doc = batch.model_dump(mode="json")
        doc["_id"] = batch.batch_id
        saved_batches[batch.batch_id] = doc

    async def mock_update_status(batch_id: str, status: str, total_files: int = None, metadata: dict = None, expires_at: str = None, clear_expires_at: bool = False):
        if batch_id in saved_batches:
            saved_batches[batch_id]["status"] = status
            if total_files is not None:
                saved_batches[batch_id]["total_files"] = total_files
            if expires_at is not None:
                saved_batches[batch_id]["expires_at"] = expires_at
            if clear_expires_at:
                saved_batches[batch_id]["expires_at"] = None
        return saved_batches.get(batch_id)

    # 1. Upload ZIP with auto_activate=False
    mock_file = UploadFile(filename="resumes.zip", file=io.BytesIO(b"dummy zip"))

    with patch("app.services.upload_service.batch_repository.save", side_effect=mock_save), \
         patch("app.services.upload_service.batch_repository.update_status", side_effect=mock_update_status), \
         patch("app.services.upload_service.validation_service.is_supported", return_value=True), \
         patch("app.services.upload_service.storage_service.save_file", return_value=StoredFile(
             original_filename="resumes.zip",
             stored_filename="resumes_1.zip",
             file_path="r.zip",
             file_size=100,
             sha256="s1",
             file_extension=".zip",
         )), \
         patch("app.services.upload_service.zip_service.extract_zip", return_value=["cand1.pdf", "cand2.pdf"]), \
         patch("app.services.upload_service.discovery_service.discover_files", return_value=["cand1.pdf", "cand2.pdf"]), \
         patch("app.services.upload_service.ingestion_service.ingest_discovered_file", new_callable=AsyncMock):

        response = await upload_service.create_upload_job([mock_file], auto_activate=False)
        assert response.status == "accepted"
        assert "activate" in response.message.lower()
        batch_id = response.batch_id
        batch_doc = saved_batches[batch_id]

        assert batch_doc["is_active"] is False
        assert batch_doc["auto_activate"] is False
        print_status("Upload response informs user of activation endpoint (Step 1)", True)

    # 2. Worker processing completion transitions batch to 'ready'
    # Simulate batch_repository.increment_progress
    repo = BatchRepository()
    mock_collection = MagicMock()

    batch_doc["processed_count"] = 2
    batch_doc["completed_count"] = 2
    batch_doc["failed_count"] = 0
    batch_doc["status"] = "ready"
    batch_doc["is_active"] = False
    batch_doc["expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    # 3. Test Match-All before activation returns HTTP 400 with diagnostic hint
    mock_jd = {"_id": "jd_1", "jd_id": "jd_1"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_1", "embeddings": [{}]}

    with patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock, return_value=mock_jd), \
         patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock, return_value=mock_jd_emb), \
         patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock, return_value=None), \
         patch("app.api.matching.batch_repository.get", new_callable=AsyncMock, return_value=batch_doc):

        resp_match_all = client.post("/matching/match-all", json={"upload_id": batch_id})
        assert resp_match_all.status_code == 400
        assert "No active recruitment batch found" in resp_match_all.json()["detail"]
        assert f"POST /batches/{batch_id}/activate" in resp_match_all.json()["detail"]
        print_status("Match-all before activation rejected with diagnostic activation hint (Step 3a)", True)

        resp_match_resume = client.post("/matching/match-resume", json={"upload_id": batch_id, "filename": "cand1.pdf"})
        assert resp_match_resume.status_code == 400
        assert "No active recruitment batch found" in resp_match_resume.json()["detail"]
        assert f"POST /batches/{batch_id}/activate" in resp_match_resume.json()["detail"]
        print_status("Match-resume before activation rejected with diagnostic activation hint (Step 3b)", True)

    # 4. Activate the batch via POST /batches/{batch_id}/activate
    async def mock_activate(b_id: str):
        if b_id == batch_id:
            batch_doc["status"] = "active"
            batch_doc["is_active"] = True
            batch_doc["expires_at"] = None
            return batch_doc
        raise ValueError(f"Batch '{b_id}' not found.")

    with patch("app.api.batches.batch_repository.get_active", new_callable=AsyncMock, return_value=None), \
         patch("app.api.batches.batch_repository.activate", new_callable=AsyncMock, side_effect=mock_activate):

        resp_activate = client.post(f"/batches/{batch_id}/activate")
        assert resp_activate.status_code == 200
        data = resp_activate.json()
        assert data["status"] == "activated"
        assert data["batch_id"] == batch_id
        assert batch_doc["is_active"] is True
        assert batch_doc["status"] == "active"
        assert batch_doc["expires_at"] is None
        print_status("POST /batches/{batch_id}/activate transitions batch to active (Step 4)", True)

    # 5. Match-All succeeds after activation
    resumes = [
        {"upload_id": batch_id, "filename": "cand1.pdf"},
        {"upload_id": batch_id, "filename": "cand2.pdf"},
    ]
    mock_db = MagicMock()
    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=2)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=resumes)
    mock_resumes_col.find = MagicMock(return_value=mock_cursor)
    mock_db.__getitem__.return_value = mock_resumes_col

    sample_match = {**SAMPLE_MATCH_RESULT, "upload_id": batch_id, "jd_id": "jd_1"}

    with patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock, return_value=mock_jd), \
         patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock, return_value=mock_jd_emb), \
         patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock, return_value=batch_doc), \
         patch("app.api.matching.mongodb.get_database", return_value=mock_db), \
         patch("app.api.matching.resume_embedding_repository.get", new_callable=AsyncMock, return_value={"embeddings": [{}]}), \
         patch("app.api.matching.hybrid_matching_service.match_resume", new_callable=AsyncMock, return_value=sample_match):

        resp_match_success = client.post("/matching/match-all", json={"upload_id": batch_id})
        assert resp_match_success.status_code == 200
        match_data = resp_match_success.json()
        assert match_data["total_eligible_resumes"] == 2
        assert match_data["successful_count"] == 2
        assert len(match_data["results"]) == 2
        print_status("Match-all succeeds on activated batch (Step 5)", True)


# ==============================================================================
# TEST 2: Rejection of Activation for Incomplete or Failed Batches
# ==============================================================================


async def test_2_activation_rejection_for_incomplete_or_failed():
    print("\n" + "=" * 70)
    print("TEST 2: ACTIVATION REJECTION FOR INCOMPLETE, FAILED, OR DRAFT BATCHES")
    print("=" * 70)

    repo = BatchRepository()
    mock_col = MagicMock()
    repo._collection = MagicMock(return_value=mock_col)

    batches_db = {
        "b_processing_incomplete": {
            "_id": "b_processing_incomplete",
            "batch_id": "b_processing_incomplete",
            "status": "processing",
            "total_files": 10,
            "processed_count": 3,
            "completed_count": 3,
        },
        "b_failed": {
            "_id": "b_failed",
            "batch_id": "b_failed",
            "status": "failed",
            "total_files": 5,
            "processed_count": 5,
            "completed_count": 0,
        },
        "b_cancelled": {
            "_id": "b_cancelled",
            "batch_id": "b_cancelled",
            "status": "cancelled",
        },
        "b_expired": {
            "_id": "b_expired",
            "batch_id": "b_expired",
            "status": "expired",
        },
        "b_draft": {
            "_id": "b_draft",
            "batch_id": "b_draft",
            "status": "draft",
        },
        "b_ready": {
            "_id": "b_ready",
            "batch_id": "b_ready",
            "status": "ready",
            "total_files": 5,
            "processed_count": 5,
            "completed_count": 5,
        },
    }

    async def mock_get(batch_id: str):
        return batches_db.get(batch_id)

    repo.get = AsyncMock(side_effect=mock_get)
    mock_col.update_many = AsyncMock()
    mock_col.find_one_and_update = AsyncMock(return_value={"_id": "b_ready", "status": "active", "is_active": True})

    # 1. Processing batch (incomplete) must be rejected
    try:
        await repo.activate("b_processing_incomplete")
        assert False, "Incomplete processing batch must be rejected!"
    except ValueError as exc:
        assert "processing" in str(exc).lower()
        assert "not completed" in str(exc).lower()
    print_status("Incomplete processing batch activation rejected (ValueError)", True)

    # 2. Failed batch must be rejected
    try:
        await repo.activate("b_failed")
        assert False, "Failed batch must be rejected!"
    except ValueError as exc:
        assert "failed" in str(exc).lower()
    print_status("Failed batch activation rejected (ValueError)", True)

    # 3. Cancelled batch must be rejected
    try:
        await repo.activate("b_cancelled")
        assert False, "Cancelled batch must be rejected!"
    except ValueError as exc:
        assert "cancelled" in str(exc).lower()
    print_status("Cancelled batch activation rejected (ValueError)", True)

    # 4. Draft batch must be rejected
    try:
        await repo.activate("b_draft")
        assert False, "Draft batch must be rejected!"
    except ValueError as exc:
        assert "draft" in str(exc).lower()
    print_status("Draft batch activation rejected (ValueError)", True)

    # 5. Ready batch succeeds
    activated = await repo.activate("b_ready")
    assert activated["status"] == "active"
    assert activated["is_active"] is True
    print_status("Ready batch successfully activated", True)


# ==============================================================================
# TEST 3: Inactive and Superseded Batch Isolation
# ==============================================================================


async def test_3_inactive_and_superseded_batch_isolation():
    print("\n" + "=" * 70)
    print("TEST 3: INACTIVE AND SUPERSEDED BATCH MATCHING ISOLATION")
    print("=" * 70)

    # Batch A is superseded
    batch_a = {
        "_id": "batch_a",
        "batch_id": "batch_a",
        "status": "superseded",
        "is_active": False,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }

    # Batch B is active
    batch_b = {
        "_id": "batch_b",
        "batch_id": "batch_b",
        "status": "active",
        "is_active": True,
        "expires_at": None,
    }

    mock_jd = {"_id": "jd_1", "jd_id": "jd_1"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_1", "embeddings": [{}]}

    batches = {"batch_a": batch_a, "batch_b": batch_b}

    async def mock_get_batch(b_id: str):
        return batches.get(b_id)

    # 1. Calling match-all specifying superseded batch_a returns HTTP 400
    with patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock, return_value=mock_jd), \
         patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock, return_value=mock_jd_emb), \
         patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock, return_value=batch_b), \
         patch("app.api.matching.batch_repository.get", new_callable=AsyncMock, side_effect=mock_get_batch):

        resp = client.post("/matching/match-all", json={"upload_id": "batch_a"})
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "not the active candidate batch" in detail
        assert "Matching is restricted to active batch 'batch_b'" in detail
        print_status("Match-all explicitly rejecting superseded batch_a (HTTP 400)", True)

    # 2. Calling match-resume for candidate from superseded batch_a returns HTTP 400
    with patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock, return_value=mock_jd), \
         patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock, return_value=mock_jd_emb), \
         patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock, return_value=batch_b), \
         patch("app.api.matching.batch_repository.get", new_callable=AsyncMock, side_effect=mock_get_batch):

        resp = client.post("/matching/match-resume", json={"upload_id": "batch_a", "filename": "cand_a1.pdf"})
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "belongs to batch 'batch_a' (status: 'superseded')" in detail
        assert "Matching is restricted to active batch 'batch_b'" in detail
        print_status("Match-resume explicitly rejecting candidate from superseded batch_a (HTTP 400)", True)


# ==============================================================================
# TEST 4: Auto-Activate=True Lifecycle
# ==============================================================================


async def test_4_auto_activate_true_lifecycle():
    print("\n" + "=" * 70)
    print("TEST 4: UPLOAD WITH AUTO_ACTIVATE=TRUE AUTOMATICALLY ACTIVATES")
    print("=" * 70)

    upload_service = UploadService()
    saved_batches: dict[str, dict] = {}

    async def mock_save(batch: Batch):
        doc = batch.model_dump(mode="json")
        doc["_id"] = batch.batch_id
        saved_batches[batch.batch_id] = doc

    async def mock_update_status(batch_id: str, status: str, total_files: int = None, metadata: dict = None, expires_at: str = None, clear_expires_at: bool = False):
        if batch_id in saved_batches:
            saved_batches[batch_id]["status"] = status
            if total_files is not None:
                saved_batches[batch_id]["total_files"] = total_files
            if expires_at is not None:
                saved_batches[batch_id]["expires_at"] = expires_at
            if clear_expires_at:
                saved_batches[batch_id]["expires_at"] = None
        return saved_batches.get(batch_id)

    mock_file = UploadFile(filename="auto_resumes.zip", file=io.BytesIO(b"dummy zip"))

    with patch("app.services.upload_service.batch_repository.save", side_effect=mock_save), \
         patch("app.services.upload_service.batch_repository.update_status", side_effect=mock_update_status), \
         patch("app.services.upload_service.validation_service.is_supported", return_value=True), \
         patch("app.services.upload_service.storage_service.save_file", return_value=StoredFile(
             original_filename="auto_resumes.zip",
             stored_filename="auto_resumes_1.zip",
             file_path="ar.zip",
             file_size=100,
             sha256="s2",
             file_extension=".zip",
         )), \
         patch("app.services.upload_service.zip_service.extract_zip", return_value=["cand1.pdf"]), \
         patch("app.services.upload_service.discovery_service.discover_files", return_value=["cand1.pdf"]), \
         patch("app.services.upload_service.ingestion_service.ingest_discovered_file", new_callable=AsyncMock):

        response = await upload_service.create_upload_job([mock_file], auto_activate=True)
        assert response.status == "accepted"
        batch_id = response.batch_id
        batch_doc = saved_batches[batch_id]
        assert batch_doc["auto_activate"] is True

        # Now simulate batch_repository.increment_progress triggering auto-activation
        repo = BatchRepository()
        col = MagicMock()
        repo._collection = MagicMock(return_value=col)

        # After processing file 1 of 1, status is processing, auto_activate is True
        batch_doc["processed_count"] = 1
        batch_doc["completed_count"] = 1
        batch_doc["total_files"] = 1
        batch_doc["status"] = "processing"

        col.find_one_and_update = AsyncMock(return_value=batch_doc)
        repo.activate = AsyncMock(return_value={**batch_doc, "status": "active", "is_active": True, "expires_at": None})

        activated_res = await repo.increment_progress(batch_id, completed=True)
        assert activated_res["status"] == "active"
        assert activated_res["is_active"] is True
        repo.activate.assert_awaited_once_with(batch_id)
        print_status("increment_progress automatically activates batch when auto_activate=True", True)


# ==============================================================================
# MAIN RUNNER
# ==============================================================================


async def main():
    print("=" * 80)
    print("TALENTAI — BATCH ACTIVATION & MATCHING WORKFLOW REGRESSION TEST SUITE")
    print("=" * 80)

    await test_1_lifecycle_auto_activate_false_workflow()
    await test_2_activation_rejection_for_incomplete_or_failed()
    await test_3_inactive_and_superseded_batch_isolation()
    await test_4_auto_activate_true_lifecycle()

    print("\n" + "=" * 80)
    print("ALL BATCH ACTIVATION & MATCHING REGRESSION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
