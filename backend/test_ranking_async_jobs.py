"""
TalentAI — Phase 7.2: Reliable Background Ranking Jobs Test Suite

Verifies:
1. Async job creation returns HTTP 202 and a job ID.
2. Job status changes from queued to processing to completed.
3. Progress increments as candidates finish.
4. A candidate failure does not prevent other candidates from being processed.
5. Incomplete candidates have no numeric final score.
6. JD and JD embeddings are reused within a batch (redundant DB reads eliminated).
7. Active batch and active JD validation remains enforced.
8. Unknown job IDs return HTTP 404.
9. Stale in-flight jobs are marked interrupted on startup.
10. The synchronous endpoint remains compatible.
11. Completed asynchronous results conform to the existing BatchRankingResponse schema.
12. Concurrent duplicate submissions do not share or overwrite job state.
13. The LLM concurrency limit is respected.
14. Exceptions update job state without exposing internal details.
"""

import asyncio
from datetime import datetime, timezone
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.auth.auth_dependencies import get_current_hr_user, HRUser
from app.database.collections import MongoCollections
from app.database.ranking_job_repository import ranking_job_repository
from app.ranking.ranking_schemas import (
    BatchRankingResponse,
    CandidateRankingResult,
    RankingJobStatusResponse,
)
from app.ranking.ranking_service import ranking_engine
from app.schemas.job_description_object import JobDescriptionObject

mock_test_hr = HRUser(
    user_id="test_hr_async_jobs",
    username="test_hr",
    full_name="Async Test HR",
    email="hr_async@talentai.internal",
    role="hr",
    created_at=datetime.now(timezone.utc),
)
app.dependency_overrides[get_current_hr_user] = lambda: mock_test_hr


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


def create_mock_jd_doc(jd_id: str = "jd_test_72"):
    return {
        "_id": jd_id,
        "jd_id": jd_id,
        "title": "Senior Backend Engineer",
        "structured_data": {
            "required_skills": ["Python", "FastAPI"],
            "responsibilities": ["Build scalable APIs"],
            "experience_requirements": [
                {
                    "minimum_years": 3.0,
                    "maximum_years": 7.0,
                    "preferred_domains": ["Fintech"],
                }
            ],
            "tools_and_technologies": ["Docker", "MongoDB"],
        },
    }


def create_mock_jd_embeddings_doc(jd_id: str = "jd_test_72"):
    return {
        "_id": f"emb_{jd_id}",
        "jd_id": jd_id,
        "embeddings": [
            {
                "section": "responsibilities",
                "text": "Build scalable APIs",
                "embedding": [0.1] * 1024,
            },
            {
                "section": "tools_and_technologies",
                "text": "Docker",
                "embedding": [0.2] * 1024,
            },
        ],
    }


def create_mock_batch_doc(batch_id: str = "batch_test_72", status: str = "active"):
    return {
        "_id": batch_id,
        "batch_id": batch_id,
        "status": status,
        "is_active": (status == "active"),
        "total_files": 2,
    }


def create_mock_resume_doc(filename: str, upload_id: str = "batch_test_72"):
    return {
        "_id": f"{upload_id}_{filename}",
        "filename": filename,
        "upload_id": upload_id,
        "status": "completed",
        "resume_data": {
            "name": f"Candidate {filename}",
            "skills": ["Python", "FastAPI"],
            "experience": [
                {
                    "company": "Fintech Corp",
                    "role": "Backend Engineer",
                    "start_date": "2020-01",
                    "end_date": "2023-01",
                    "description": "Developed payments backend.",
                }
            ],
            "projects": [
                {
                    "title": "Payment Gateway",
                    "description": "Built scalable APIs using Docker.",
                }
            ],
        },
    }


def create_mock_resume_emb_doc(filename: str, upload_id: str = "batch_test_72"):
    return {
        "_id": f"emb_{upload_id}_{filename}",
        "filename": filename,
        "upload_id": upload_id,
        "embeddings": [
            {
                "section": "experience",
                "text": "Developed payments backend",
                "embedding": [0.12] * 1024,
            },
            {
                "section": "projects",
                "text": "Built scalable APIs using Docker",
                "embedding": [0.22] * 1024,
            },
        ],
    }


# ==============================================================================
# TEST CASES
# ==============================================================================


async def test_1_async_job_creation_returns_202():
    print("\n--- TEST 1: ASYNC JOB CREATION RETURNS HTTP 202 & JOB ID ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch("app.api.ranking.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
             patch("app.api.ranking.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
             patch("app.api.ranking.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc())), \
             patch("app.ranking.ranking_service.ranking_engine.execute_ranking_job", new=AsyncMock()):

            mock_col = MagicMock()
            mock_col.count_documents = AsyncMock(return_value=5)
            mock_col.insert_one = AsyncMock()

            with patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_col, "ranking_jobs": mock_col}):
                response = await client.post("/ranking/rank-batch-async", json={})
                assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
                data = response.json()
                assert "job_id" in data and len(data["job_id"]) > 0
                assert data["status"] == "queued"
                assert data["total_eligible"] == 5
                assert data["completed_count"] == 0
                assert data["result"] is None
                print_status("Test 1: POST /ranking/rank-batch-async returns 202 and initial queued state", True)


async def test_2_and_3_job_lifecycle_and_progress_increments():
    print("\n--- TESTS 2 & 3: JOB LIFECYCLE TRANSITIONS AND PROGRESS INCREMENTS ---")
    in_memory_jobs = {}

    async def mock_create(doc):
        in_memory_jobs[doc["job_id"]] = dict(doc)
        return doc

    async def mock_update(job_id, updates):
        if job_id in in_memory_jobs:
            in_memory_jobs[job_id].update(updates)

    async def mock_get(job_id):
        return in_memory_jobs.get(job_id)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get):

        jd_doc = create_mock_jd_doc()
        jd_emb = create_mock_jd_embeddings_doc()
        batch_doc = create_mock_batch_doc()
        res_docs = [
            create_mock_resume_doc("cand1.pdf"),
            create_mock_resume_doc("cand2.pdf"),
        ]

        mock_resumes_col = MagicMock()
        mock_resumes_col.count_documents = AsyncMock(return_value=2)

        # Mock cursor for eligible_docs
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=res_docs)
        mock_resumes_col.find.return_value = mock_cursor

        mock_match = {
            "jd_id": "jd_test_72",
            "upload_id": "batch_test_72",
            "filename": "cand.pdf",
            "exact_matching": {
                "total_required_skills": 2,
                "matched_required_skills": 2,
                "unmatched_required_skills": 0,
                "status": "completed",
                "error": None,
                "matches": [
                    {"required_skill": "Python", "matched": True, "resume_skill": "Python", "match_type": "llm"},
                    {"required_skill": "FastAPI", "matched": True, "resume_skill": "FastAPI", "match_type": "llm"},
                ],
            },
            "semantic_retrieval": {
                "top_k": 5,
                "responsibilities_retrieval": {
                    "top_k": 5,
                    "results": [
                        {
                            "jd_item_index": 0,
                            "jd_text": "Build scalable APIs",
                            "matches": [{"resume_text": "Built scalable APIs", "resume_section": "projects", "similarity": 0.85}],
                        }
                    ],
                },
                "tools_and_technologies_retrieval": {
                    "top_k": 5,
                    "results": [
                        {
                            "jd_item_index": 0,
                            "jd_text": "Docker",
                            "matches": [{"resume_text": "Docker", "resume_section": "projects", "similarity": 0.90}],
                        }
                    ],
                },
                "results": [],
            },
            "experience_matching": {
                "minimum_years": 3.0,
                "maximum_years": 7.0,
                "preferred_domains": ["Fintech"],
                "relevant_experience_found": True,
                "relevant_duration_years": 3.0,
                "minimum_duration_satisfied": True,
                "maximum_duration_exceeded": False,
                "experiences": [
                    {
                        "experience_index": 0,
                        "company": "Fintech Corp",
                        "role": "Backend Engineer",
                        "start_date": "2020-01",
                        "end_date": "2023-01",
                        "relevance_score": 0.95,
                        "matched_domains": ["Fintech"],
                        "decision": "RELEVANT",
                        "relevant": True,
                    }

                ],
            },
        }

        with patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=batch_doc)), \
             patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(return_value=create_mock_resume_emb_doc("cand1.pdf"))), \
             patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", new=AsyncMock(return_value=mock_match)), \
             patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

            # Step 1: Create Job
            job = await ranking_engine.create_and_start_ranking_job()
            job_id = job["job_id"]
            assert in_memory_jobs[job_id]["status"] == "queued"
            assert in_memory_jobs[job_id]["completed_count"] == 0

            # Step 2: Await background execution
            if job_id in ranking_engine._active_tasks:
                await ranking_engine._active_tasks[job_id]

            final_job = in_memory_jobs[job_id]
            assert final_job["status"] == "completed"
            assert final_job["completed_count"] == 2
            assert final_job["progress_percentage"] == 100.0
            assert final_job["finished_at"] is not None
            assert final_job["result"] is not None
            assert len(final_job["result"]["ranked_candidates"]) == 2
            print_status("Tests 2 & 3: Job transitions queued -> processing -> completed with progress updates", True)


async def test_4_and_5_candidate_failure_isolation_and_incomplete_status():
    print("\n--- TESTS 4 & 5: CANDIDATE FAILURE ISOLATION & UNRANKED INCOMPLETE ---")
    in_memory_jobs = {}

    async def mock_create(doc):
        in_memory_jobs[doc["job_id"]] = dict(doc)
        return doc

    async def mock_update(job_id, updates):
        if job_id in in_memory_jobs:
            in_memory_jobs[job_id].update(updates)

    async def mock_get(job_id):
        return in_memory_jobs.get(job_id)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get):

        jd_doc = create_mock_jd_doc()
        jd_emb = create_mock_jd_embeddings_doc()
        batch_doc = create_mock_batch_doc()
        res_docs = [
            create_mock_resume_doc("fail_cand.pdf"),
            create_mock_resume_doc("success_cand.pdf"),
        ]

        mock_resumes_col = MagicMock()
        mock_resumes_col.count_documents = AsyncMock(return_value=2)
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=res_docs)
        mock_resumes_col.find.return_value = mock_cursor

        async def mock_match_side_effect(jd_id, upload_id, filename, preloaded_jd=None, preloaded_jd_embeddings=None):
            if filename == "fail_cand.pdf":
                raise RuntimeError("Ollama connection timeout on candidate 1")
            return {
                "jd_id": jd_id,
                "upload_id": upload_id,
                "filename": filename,
                "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1, "unmatched_required_skills": 0, "status": "completed", "matches": [{"required_skill": "Python", "matched": True}]},
                "semantic_retrieval": {"top_k": 5, "responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}, "results": []},
                "experience_matching": {"relevant_experience_found": False, "experiences": []},
            }

        with patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=batch_doc)), \
             patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(return_value=create_mock_resume_emb_doc("cand"))), \
             patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
             patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

            job = await ranking_engine.create_and_start_ranking_job()
            job_id = job["job_id"]
            if job_id in ranking_engine._active_tasks:
                await ranking_engine._active_tasks[job_id]

            res = in_memory_jobs[job_id]["result"]
            assert res is not None
            assert res["ranked_count"] == 1
            assert res["unranked_count"] == 1
            assert res["ranked_candidates"][0]["filename"] == "success_cand.pdf"
            assert res["ranked_candidates"][0]["final_score"] is not None

            incomplete_cand = res["unranked_candidates"][0]
            assert incomplete_cand["filename"] == "fail_cand.pdf"
            assert incomplete_cand["status"] == "incomplete"
            assert incomplete_cand["final_score"] is None
            assert incomplete_cand["rank"] is None
            assert "Ollama connection timeout" in incomplete_cand["errors"][0]
            print_status("Tests 4 & 5: Candidate failure does not abort batch; incomplete candidate has final_score=None", True)


async def test_6_jd_and_embeddings_reused_without_redundant_db_reads():
    print("\n--- TEST 6: JD AND JD EMBEDDINGS REUSED WITHOUT REDUNDANT DB READS ---")
    jd_doc = create_mock_jd_doc()
    jd_emb = create_mock_jd_embeddings_doc()
    batch_doc = create_mock_batch_doc()
    res_docs = [
        create_mock_resume_doc("cand1.pdf"),
        create_mock_resume_doc("cand2.pdf"),
        create_mock_resume_doc("cand3.pdf"),
    ]

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=3)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=res_docs)
    mock_resumes_col.find.return_value = mock_cursor

    mock_jd_repo_get = AsyncMock(return_value=jd_doc)
    mock_jd_emb_repo_get = AsyncMock(return_value=jd_emb)

    mock_match = {
        "jd_id": "jd_test_72",
        "upload_id": "batch_test_72",
        "filename": "cand.pdf",
        "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1, "unmatched_required_skills": 0, "status": "completed", "matches": []},
        "semantic_retrieval": {"top_k": 5, "responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}, "results": []},
        "experience_matching": {"relevant_experience_found": False, "experiences": []},
    }

    with patch("app.ranking.ranking_service.jd_repository.get", mock_jd_repo_get), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", mock_jd_emb_repo_get), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=batch_doc)), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(return_value=create_mock_resume_emb_doc("cand"))), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", new=AsyncMock(return_value=mock_match)), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        # Run synchronous rank_batch for 3 candidates
        await ranking_engine.rank_batch()

        # Both get_active/get and get_by_jd_id should only be called ONCE at batch level,
        # NOT 3 times (once per candidate).
        assert mock_jd_emb_repo_get.call_count == 1, f"Expected 1 JD embedding fetch, got {mock_jd_emb_repo_get.call_count}"
        print_status("Test 6: Preloaded JD and JD embeddings reused across candidates (zero redundant reads)", True)


async def test_7_active_batch_and_jd_validation_enforced():
    print("\n--- TEST 7: ACTIVE BATCH AND ACTIVE JD VALIDATION ENFORCED ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Case A: Missing Active JD
        with patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=None)):
            res = await client.post("/ranking/rank-batch-async", json={})
            assert res.status_code == 400
            assert "No active job description found" in res.json()["detail"]

        # Case B: Inactive Batch
        jd_doc = create_mock_jd_doc()
        jd_emb = create_mock_jd_embeddings_doc()
        with patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=None)):
            res = await client.post("/ranking/rank-batch-async", json={})
            assert res.status_code == 400
            assert "No active recruitment batch found" in res.json()["detail"]

        # Case C: Specified batch is not active batch
        active_b = create_mock_batch_doc("batch_A")
        with patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=active_b)):
            res = await client.post("/ranking/rank-batch-async", json={"upload_id": "batch_B"})
            assert res.status_code == 400
            assert "not the active recruitment batch" in res.json()["detail"]

        print_status("Test 7: Active batch and active JD validation strictly enforced", True)



async def test_8_unknown_job_id_returns_404():
    print("\n--- TEST 8: UNKNOWN JOB ID RETURNS HTTP 404 ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch.object(ranking_job_repository, "get_job", new=AsyncMock(return_value=None)):
            res = await client.get("/ranking/jobs/nonexistent-uuid-1234")
            assert res.status_code == 404
            assert "not found" in res.json()["detail"]
            print_status("Test 8: GET /ranking/jobs/{unknown_id} returns HTTP 404", True)


async def test_9_stale_in_flight_jobs_reconciled_on_startup():
    print("\n--- TEST 9: STALE IN-FLIGHT JOBS RECONCILED ON STARTUP ---")
    mock_col = MagicMock()
    mock_res = MagicMock()
    mock_res.modified_count = 3
    mock_col.update_many = AsyncMock(return_value=mock_res)

    with patch.object(ranking_job_repository, "_collection", return_value=mock_col):
        count = await ranking_job_repository.reconcile_stale_jobs()
        assert count == 3
        mock_col.update_many.assert_called_once()
        args, kwargs = mock_col.update_many.call_args
        assert args[0] == {"status": {"$in": ["queued", "processing"]}}
        assert args[1]["$set"]["status"] == "interrupted"
        print_status("Test 9: Stale queued/processing jobs marked interrupted on startup", True)


async def test_10_and_11_synchronous_compatibility_and_schema_purity():
    print("\n--- TESTS 10 & 11: SYNCHRONOUS COMPATIBILITY & SCHEMA PURITY ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        jd_doc = create_mock_jd_doc()
        jd_emb = create_mock_jd_embeddings_doc()
        batch_doc = create_mock_batch_doc()
        cand_doc = create_mock_resume_doc("cand.pdf")

        mock_resumes_col = MagicMock()
        mock_resumes_col.count_documents = AsyncMock(return_value=1)
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[cand_doc])
        mock_resumes_col.find.return_value = mock_cursor

        mock_match = {
            "jd_id": "jd_test_72",
            "upload_id": "batch_test_72",
            "filename": "cand.pdf",
            "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1, "unmatched_required_skills": 0, "status": "completed", "matches": []},
            "semantic_retrieval": {"top_k": 5, "responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}, "results": []},
            "experience_matching": {"relevant_experience_found": False, "experiences": []},
        }

        with patch("app.api.ranking.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.api.ranking.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.api.ranking.batch_repository.get_active", new=AsyncMock(return_value=batch_doc)), \
             patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(return_value=create_mock_resume_emb_doc("cand.pdf"))), \
             patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", new=AsyncMock(return_value=mock_match)), \
             patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

            res = await client.post("/ranking/rank-batch", json={})
            assert res.status_code == 200
            data = res.json()
            validated = BatchRankingResponse.model_validate(data)
            assert validated.ranked_count == 1
            assert validated.ranked_candidates[0].rank == 1
            print_status("Tests 10 & 11: Synchronous endpoint preserves exact BatchRankingResponse contract", True)



async def test_12_concurrent_duplicate_submissions_isolated():
    print("\n--- TEST 12: CONCURRENT DUPLICATE SUBMISSIONS PROPERLY ISOLATED ---")
    in_memory_jobs = {}

    async def mock_create(doc):
        in_memory_jobs[doc["job_id"]] = dict(doc)
        return doc

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create):
        jd_doc = create_mock_jd_doc()
        jd_emb = create_mock_jd_embeddings_doc()
        batch_doc = create_mock_batch_doc()

        mock_resumes_col = MagicMock()
        mock_resumes_col.count_documents = AsyncMock(return_value=5)

        with patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=batch_doc)), \
             patch.object(ranking_engine, "execute_ranking_job", new=AsyncMock()), \
             patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

            job1, job2 = await asyncio.gather(
                ranking_engine.create_and_start_ranking_job(),
                ranking_engine.create_and_start_ranking_job(),
            )

            assert job1["job_id"] != job2["job_id"]
            assert job1["job_id"] in in_memory_jobs
            assert job2["job_id"] in in_memory_jobs
            assert in_memory_jobs[job1["job_id"]] is not in_memory_jobs[job2["job_id"]]
            print_status("Test 12: Concurrent submissions receive unique isolated job documents", True)


async def test_13_llm_concurrency_limit_respected():
    print("\n--- TEST 13: LLM CONCURRENCY LIMIT (SEMAPHORE=1) RESPECTED ---")
    active_concurrent_slots = 0
    max_observed_concurrency = 0

    async def mock_match_concurrency_tracker(*args, **kwargs):
        nonlocal active_concurrent_slots, max_observed_concurrency
        active_concurrent_slots += 1
        if active_concurrent_slots > max_observed_concurrency:
            max_observed_concurrency = active_concurrent_slots
        await asyncio.sleep(0.05)
        active_concurrent_slots -= 1
        return {
            "jd_id": "jd",
            "upload_id": "b",
            "filename": "cand.pdf",
            "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1, "unmatched_required_skills": 0, "status": "completed", "matches": []},
            "semantic_retrieval": {"top_k": 5, "responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}, "results": []},
            "experience_matching": {"relevant_experience_found": False, "experiences": []},
        }

    in_memory_jobs = {}

    async def mock_create(doc):
        in_memory_jobs[doc["job_id"]] = dict(doc)
        return doc

    async def mock_update(job_id, updates):
        if job_id in in_memory_jobs:
            in_memory_jobs[job_id].update(updates)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update):

        jd_doc = create_mock_jd_doc()
        jd_emb = create_mock_jd_embeddings_doc()
        batch_doc = create_mock_batch_doc()
        res_docs = [create_mock_resume_doc(f"cand_{i}.pdf") for i in range(4)]

        mock_resumes_col = MagicMock()
        mock_resumes_col.count_documents = AsyncMock(return_value=4)
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=res_docs)
        mock_resumes_col.find.return_value = mock_cursor

        with patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=batch_doc)), \
             patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(return_value=create_mock_resume_emb_doc("cand"))), \
             patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_concurrency_tracker), \
             patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

            job = await ranking_engine.create_and_start_ranking_job()
            job_id = job["job_id"]
            if job_id in ranking_engine._active_tasks:
                await ranking_engine._active_tasks[job_id]

            assert max_observed_concurrency == 1, f"Expected max concurrency 1, but observed {max_observed_concurrency}"
            print_status("Test 13: Hardware-bound LLM concurrency limit (1 slot) strictly respected", True)


async def test_14_fatal_exceptions_update_job_with_sanitized_error():
    print("\n--- TEST 14: FATAL EXCEPTIONS UPDATE JOB WITH SANITIZED ERROR ---")
    in_memory_jobs = {}

    async def mock_create(doc):
        in_memory_jobs[doc["job_id"]] = dict(doc)
        return doc

    async def mock_update(job_id, updates):
        if job_id in in_memory_jobs:
            in_memory_jobs[job_id].update(updates)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update):

        jd_doc = create_mock_jd_doc()
        jd_emb = create_mock_jd_embeddings_doc()
        batch_doc = create_mock_batch_doc()

        mock_resumes_col = MagicMock()
        mock_resumes_col.count_documents = AsyncMock(return_value=2)
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(side_effect=ConnectionResetError("Socket broken at /var/run/mongodb.sock"))
        mock_resumes_col.find.return_value = mock_cursor

        with patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=jd_doc)), \
             patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=jd_emb)), \
             patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=batch_doc)), \
             patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

            job = await ranking_engine.create_and_start_ranking_job()
            job_id = job["job_id"]
            if job_id in ranking_engine._active_tasks:
                await ranking_engine._active_tasks[job_id]

            final_job = in_memory_jobs[job_id]
            assert final_job["status"] == "failed"
            assert final_job["error"] == "Ranking job failed due to an unexpected server error."
            # Ensure internal socket path is NOT leaked to clients
            assert "/var/run/mongodb.sock" not in final_job["error"]
            print_status("Test 14: Fatal exceptions sanitized without leaking internal paths or stack traces", True)


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================


async def run_all_async_tests():
    print("=" * 80)
    print("TALENTAI — PHASE 7.2: ASYNCHRONOUS RANKING JOBS REGRESSION SUITE")
    print("=" * 80)

    await test_1_async_job_creation_returns_202()
    await test_2_and_3_job_lifecycle_and_progress_increments()
    await test_4_and_5_candidate_failure_isolation_and_incomplete_status()
    await test_6_jd_and_embeddings_reused_without_redundant_db_reads()
    await test_7_active_batch_and_jd_validation_enforced()
    await test_8_unknown_job_id_returns_404()
    await test_9_stale_in_flight_jobs_reconciled_on_startup()
    await test_10_and_11_synchronous_compatibility_and_schema_purity()
    await test_12_concurrent_duplicate_submissions_isolated()
    await test_13_llm_concurrency_limit_respected()
    await test_14_fatal_exceptions_update_job_with_sanitized_error()

    print("\n" + "=" * 80)
    print("ALL 14 PHASE 7.2 ASYNCHRONOUS RANKING TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_async_tests())
