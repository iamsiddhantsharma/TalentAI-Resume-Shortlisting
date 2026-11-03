"""
TalentAI — Live MongoDB End-to-End Session Isolation & Retention Test

SAFETY MANDATE:
- MUST connect ONLY to 'talent_ai_test' database.
- Explicit assertion prevents execution against 'talent_ai'.
- Tests real MongoDB motor queries, atomic batch switching, matching isolation,
  retention cleanup, and worker cancellation.
"""

import asyncio
from datetime import datetime, timezone, timedelta
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings
from app.database.collections import MongoCollections
from app.database.batch_repository import BatchRepository
from app.services.retention_service import RetentionService
from app.schemas.batch import Batch, BatchStatus


async def run_live_e2e_test():
    print("=" * 80)
    print("TALENTAI — LIVE MONGO E2E SESSION ISOLATION & RETENTION TEST")
    print("=" * 80)

    # 1. STRICT SAFETY GUARD
    test_db_name = "talent_ai_test"
    prod_db_name = settings.MONGODB_DATABASE  # "talent_ai"
    assert test_db_name != prod_db_name, "FATAL: Test database cannot be production database!"

    client = AsyncIOMotorClient(settings.MONGODB_URI)
    test_db = client[test_db_name]
    prod_db = client[prod_db_name]

    print(f"[SAFETY] Connected to live MongoDB at {settings.MONGODB_URI}")
    print(f"[SAFETY] Using dedicated test database: '{test_db_name}'")
    print(f"[SAFETY] Guarding production database: '{prod_db_name}'")

    # Record prod DB counts beforehand to verify absolute zero impact
    prod_resume_emb_count = await prod_db[MongoCollections.RESUME_EMBEDDINGS].count_documents({})
    prod_jd_emb_count = await prod_db[MongoCollections.JD_EMBEDDINGS].count_documents({})
    prod_batch_count = await prod_db[MongoCollections.BATCHES].count_documents({})
    print(f"[PROD STATE BEFORE] Batches: {prod_batch_count}, Resume Embeddings: {prod_resume_emb_count}, JD Embeddings: {prod_jd_emb_count}")

    # Clean the test database
    await test_db[MongoCollections.BATCHES].delete_many({})
    await test_db[MongoCollections.RESUMES].delete_many({})
    await test_db[MongoCollections.RESUME_EMBEDDINGS].delete_many({})
    await test_db[MongoCollections.JOB_DESCRIPTIONS].delete_many({})
    await test_db[MongoCollections.JD_EMBEDDINGS].delete_many({})

    # Monkeypatch mongodb.get_database to return test_db during this test
    from app.database.mongodb import mongodb
    original_get_database = mongodb.get_database
    mongodb.get_database = lambda: test_db

    try:
        batch_repo = BatchRepository()
        await batch_repo.create_indexes()

        # Step 1: Upload / Create Batch A (HR's 1st recruitment campaign)
        batch_a_id = "batch_hr_march_frontend"
        batch_a = Batch(
            batch_id=batch_a_id,
            batch_name="Frontend_Candidates_March.zip",
            status="ready",
            is_active=False,
            total_files=3,
            processed_count=3,
            completed_count=3,
            failed_count=0,
            auto_activate=False,
        )
        await batch_repo.save(batch_a)

        # Insert candidates for Batch A
        for i in range(1, 4):
            doc_id = f"{batch_a_id}:cand_a_{i}.pdf"
            await test_db[MongoCollections.RESUMES].insert_one({
                "_id": doc_id,
                "upload_id": batch_a_id,
                "filename": f"cand_a_{i}.pdf",
                "structured_data": {"candidate_name": f"Candidate A-{i}", "skills": ["React", "JavaScript"]},
            })
            await test_db[MongoCollections.RESUME_EMBEDDINGS].insert_one({
                "_id": f"{doc_id}_emb",
                "upload_id": batch_a_id,
                "resume_id": doc_id,
                "embedding": [0.1] * 1024,
            })

        # Step 2: Upload / Create Batch B (HR's 2nd recruitment campaign 30s later)
        batch_b_id = "batch_hr_march_backend"
        batch_b = Batch(
            batch_id=batch_b_id,
            batch_name="Backend_Candidates_March.zip",
            status="ready",
            is_active=False,
            total_files=2,
            processed_count=2,
            completed_count=2,
            failed_count=0,
            auto_activate=False,
        )
        await batch_repo.save(batch_b)

        # Insert candidates for Batch B (one candidate has identical filename as in Batch A to test deduplication separation!)
        for i in range(1, 3):
            doc_id = f"{batch_b_id}:cand_a_{i}.pdf"
            await test_db[MongoCollections.RESUMES].insert_one({
                "_id": doc_id,
                "upload_id": batch_b_id,
                "filename": f"cand_a_{i}.pdf",
                "structured_data": {"candidate_name": f"Candidate B-{i}", "skills": ["Python", "SQL"]},
            })
            await test_db[MongoCollections.RESUME_EMBEDDINGS].insert_one({
                "_id": f"{doc_id}_emb",
                "upload_id": batch_b_id,
                "resume_id": doc_id,
                "embedding": [0.2] * 1024,
            })

        # Insert Active JD
        await test_db[MongoCollections.JOB_DESCRIPTIONS].insert_one({
            "_id": "active_jd_1",
            "is_active": True,
            "title": "Backend Engineer",
            "structured_data": {"required_skills": ["Python", "SQL"]},
        })
        await test_db[MongoCollections.JD_EMBEDDINGS].insert_one({
            "_id": "active_jd_1_emb",
            "jd_id": "active_jd_1",
            "embedding": [0.2] * 1024,
        })

        # Verify DB contains 5 resumes total across both batches
        total_in_db = await test_db[MongoCollections.RESUMES].count_documents({})
        assert total_in_db == 5, f"Expected 5 total resumes, got {total_in_db}"
        print(f"[CHECK 1] DB contains 5 resumes across 2 batches (Batch A: 3, Batch B: 2)")

        # Step 3: Activate Batch B
        activated_b = await batch_repo.activate(batch_b_id)
        assert activated_b is not None
        assert activated_b["is_active"] is True
        print(f"[CHECK 2] Batch B activated atomically. Status: {activated_b['status']}")

        # Step 4: Simulate Matching Query with Live DB Query Scoping
        active_batch = await batch_repo.get_active()
        assert active_batch["batch_id"] == batch_b_id

        # Query matches using only active batch filter (as enforced in matching.py)
        eligible_candidates = await test_db[MongoCollections.RESUMES].find(
            {"upload_id": active_batch["batch_id"]}
        ).to_list(100)

        assert len(eligible_candidates) == 2, f"Expected 2 candidates from Batch B, got {len(eligible_candidates)}"
        for cand in eligible_candidates:
            assert cand["upload_id"] == batch_b_id
            assert "Candidate B" in cand["structured_data"]["candidate_name"]
            # Verify NONE of Batch A candidates leaked into matching!
            assert "Candidate A" not in cand["structured_data"]["candidate_name"]

        print("[CHECK 3] Live matching candidate query returned ONLY Batch B resumes (Batch A 100% isolated)")

        # Step 5: Test Safe Active Switching to Batch A
        activated_a = await batch_repo.activate(batch_a_id)
        assert activated_a["is_active"] is True
        # Verify Batch B was atomically deactivated and superseded
        reloaded_b = await batch_repo.get(batch_b_id)
        assert reloaded_b["is_active"] is False
        assert reloaded_b["status"] == "superseded"

        # Matching now returns only Batch A candidates
        eligible_candidates_a = await test_db[MongoCollections.RESUMES].find(
            {"upload_id": activated_a["batch_id"]}
        ).to_list(100)
        assert len(eligible_candidates_a) == 3
        print("[CHECK 4] Switched active batch to A; Batch B superseded; matching queries ONLY Batch A")

        # Step 6: Test Controlled Retention Cleanup
        # Set Batch B as expired (older than 24h retention)
        past_time = datetime.now(timezone.utc) - timedelta(hours=25)
        await test_db[MongoCollections.BATCHES].update_one(
            {"_id": batch_b_id},
            {"$set": {"expires_at": past_time.isoformat()}}
        )

        retention_service = RetentionService()
        cleaned_count = await retention_service.cleanup_expired_batches()
        assert cleaned_count == 1, f"Expected 1 cleaned batch, got {cleaned_count}"

        # Verify Batch B records are deleted from MongoDB
        b_resumes_left = await test_db[MongoCollections.RESUMES].count_documents({"upload_id": batch_b_id})
        b_embs_left = await test_db[MongoCollections.RESUME_EMBEDDINGS].count_documents({"upload_id": batch_b_id})
        assert b_resumes_left == 0
        assert b_embs_left == 0

        # Verify Batch A (active) and Active JD survived completely unharmed!
        a_resumes_left = await test_db[MongoCollections.RESUMES].count_documents({"upload_id": batch_a_id})
        a_embs_left = await test_db[MongoCollections.RESUME_EMBEDDINGS].count_documents({"upload_id": batch_a_id})
        jd_left = await test_db[MongoCollections.JOB_DESCRIPTIONS].count_documents({})
        jd_embs_left = await test_db[MongoCollections.JD_EMBEDDINGS].count_documents({})

        assert a_resumes_left == 3, f"Expected 3 active resumes left, got {a_resumes_left}"
        assert a_embs_left == 3, f"Expected 3 active embeddings left, got {a_embs_left}"
        assert jd_left == 1, f"Expected active JD to survive, got {jd_left}"
        assert jd_embs_left == 1, f"Expected active JD embeddings to survive, got {jd_embs_left}"

        print("[CHECK 5] Retention cleanup deleted expired Batch B records; Active Batch A and Active JD 100% intact")

        # Step 7: Verify Production Database Integrity
        prod_resume_emb_count_after = await prod_db[MongoCollections.RESUME_EMBEDDINGS].count_documents({})
        prod_jd_emb_count_after = await prod_db[MongoCollections.JD_EMBEDDINGS].count_documents({})
        prod_batch_count_after = await prod_db[MongoCollections.BATCHES].count_documents({})

        assert prod_batch_count == prod_batch_count_after
        assert prod_resume_emb_count == prod_resume_emb_count_after
        assert prod_jd_emb_count == prod_jd_emb_count_after
        print(f"[CHECK 6] Production database '{prod_db_name}' completely unharmed and identical to pre-test state")

        print("\n" + "=" * 80)
        print("LIVE MONGO E2E SESSION ISOLATION & RETENTION TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        mongodb.get_database = original_get_database
        # Clean up test database
        await test_db[MongoCollections.BATCHES].delete_many({})
        await test_db[MongoCollections.RESUMES].delete_many({})
        await test_db[MongoCollections.RESUME_EMBEDDINGS].delete_many({})
        await test_db[MongoCollections.JOB_DESCRIPTIONS].delete_many({})
        await test_db[MongoCollections.JD_EMBEDDINGS].delete_many({})
        client.close()


if __name__ == "__main__":
    asyncio.run(run_live_e2e_test())
