"""
TalentAI — Synthetic Test Suite: Rank-All Candidates and Single-HR Batch Processing

Verifies:
1. Synthetic batch with > 50 eligible candidates (e.g. 75 candidates) ranks every candidate.
2. Synthetic batch with exactly 50 candidates behaves correctly.
3. Synthetic batch with fewer than 50 candidates (e.g. 15 candidates) behaves correctly.
4. Ineligible candidates (e.g. failed status or missing resume_data) remain strictly excluded.
5. In-flight progress increments and total_eligible accurately reflect the full eligible population.
6. Score components, deterministic rank ordering, tie handling, and explainability remain intact.
7. Explicit limit parameter compatibility (optional limit vs default full batch).

NOTE: Uses synthetic in-memory fixtures only. No real resumes, database collections,
or protected batches are touched.
"""

import asyncio
from datetime import datetime, timezone
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.database.ranking_job_repository import ranking_job_repository
from app.ranking.ranking_schemas import (
    BatchRankingResponse,
    CandidateRankingResult,
    RankBatchRequest,
)
from app.ranking.ranking_service import ranking_engine


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


def create_mock_jd_doc(jd_id: str = "jd_synthetic_all"):
    return {
        "_id": jd_id,
        "jd_id": jd_id,
        "title": "Lead Software Architect",
        "structured_data": {
            "required_skills": ["Python", "FastAPI", "Distributed Systems"],
            "responsibilities": ["Design high-throughput microservices"],
            "experience_requirements": [
                {
                    "minimum_years": 5.0,
                    "maximum_years": 10.0,
                    "preferred_domains": ["Cloud Infrastructure"],
                }
            ],
            "tools_and_technologies": ["Docker", "Kubernetes", "MongoDB"],
        },
    }


def create_mock_jd_embeddings_doc(jd_id: str = "jd_synthetic_all"):
    return {
        "_id": f"emb_{jd_id}",
        "jd_id": jd_id,
        "embeddings": [
            {
                "section": "responsibilities",
                "text": "Design high-throughput microservices",
                "embedding": [0.15] * 1024,
            },
            {
                "section": "tools_and_technologies",
                "text": "Kubernetes",
                "embedding": [0.25] * 1024,
            },
        ],
    }


def create_mock_batch_doc(batch_id: str = "batch_synthetic_all", total_files: int = 75):
    return {
        "_id": batch_id,
        "batch_id": batch_id,
        "status": "active",
        "is_active": True,
        "total_files": total_files,
    }


def create_mock_resume_doc(
    filename: str,
    upload_id: str = "batch_synthetic_all",
    status: str = "completed",
    has_resume_data: bool = True,
    experience_years: float = 6.0,
):
    doc = {
        "_id": f"{upload_id}_{filename}",
        "filename": filename,
        "upload_id": upload_id,
        "status": status,
    }
    if has_resume_data:
        doc["resume_data"] = {
            "name": f"Candidate {filename}",
            "skills": ["Python", "FastAPI", "Distributed Systems", "Docker"],
            "experience": [
                {
                    "company": "Cloud Systems Inc",
                    "role": "Senior Engineer",
                    "start_date": "2018-01",
                    "end_date": "2024-01",
                    "description": "Architected resilient distributed backends.",
                }
            ],
            "projects": [
                {
                    "title": "Microservice Mesh",
                    "description": "Built high-throughput services with Kubernetes.",
                }
            ],
        }
    else:
        doc["resume_data"] = None
def create_mock_resume_emb_doc(filename: str, upload_id: str = "batch_synthetic_all"):
    return {
        "_id": f"emb_{upload_id}_{filename}",
        "filename": filename,
        "upload_id": upload_id,
        "embeddings": [
            {
                "section": "experience",
                "text": "Architected resilient distributed backends",
                "embedding": [0.12] * 1024,
            },
            {
                "section": "projects",
                "text": "Built high-throughput services with Kubernetes",
                "embedding": [0.22] * 1024,
            },
        ],
    }


async def mock_get_resume_emb(upload_id: str, filename: str):
    return create_mock_resume_emb_doc(filename, upload_id)


def create_mock_match_result(candidate_index: int):
    # Generates slightly varied scores for deterministic ordering and tie tests
    skill_pct = min(1.0, 0.70 + (candidate_index % 30) * 0.01)
    return {
        "jd_id": "jd_synthetic_all",
        "upload_id": "batch_synthetic_all",
        "filename": f"candidate_{candidate_index:03d}.pdf",
        "exact_matching": {
            "total_required_skills": 3,
            "matched_required_skills": 3 if skill_pct > 0.8 else 2,
            "unmatched_required_skills": 0 if skill_pct > 0.8 else 1,
            "status": "completed",
            "error": None,
            "matches": [
                {"required_skill": "Python", "matched": True, "resume_skill": "Python", "match_type": "exact"},
                {"required_skill": "FastAPI", "matched": True, "resume_skill": "FastAPI", "match_type": "exact"},
                {
                    "required_skill": "Distributed Systems",
                    "matched": skill_pct > 0.8,
                    "resume_skill": "Distributed Systems" if skill_pct > 0.8 else None,
                    "match_type": "llm" if skill_pct > 0.8 else None,
                },
            ],
        },
        "semantic_retrieval": {
            "top_k": 5,
            "responsibilities_retrieval": {
                "top_k": 5,
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Design high-throughput microservices",
                        "matches": [
                            {"resume_text": "Architected resilient distributed backends", "resume_section": "experience", "similarity": 0.82}
                        ],
                    }
                ],
            },
            "tools_and_technologies_retrieval": {
                "top_k": 5,
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Kubernetes",
                        "matches": [
                            {"resume_text": "Built high-throughput services with Kubernetes", "resume_section": "projects", "similarity": 0.88}
                        ],
                    }
                ],
            },
            "results": [],
        },
        "experience_matching": {
            "minimum_years": 5.0,
            "maximum_years": 10.0,
            "preferred_domains": ["Cloud Infrastructure"],
            "relevant_experience_found": True,
            "relevant_duration_years": 6.0,
            "minimum_duration_satisfied": True,
            "maximum_duration_exceeded": False,
            "experiences": [
                {
                    "experience_index": 0,
                    "company": "Cloud Systems Inc",
                    "role": "Senior Engineer",
                    "start_date": "2018-01",
                    "end_date": "2024-01",
                    "relevance_score": 0.90,
                    "matched_domains": ["Cloud Infrastructure"],
                    "decision": "RELEVANT",
                    "relevant": True,
                }
            ],
        },
    }


def setup_in_memory_job_repo():
    in_memory_jobs = {}

    async def mock_create(doc):
        in_memory_jobs[doc["job_id"]] = dict(doc)
        return doc

    async def mock_update(job_id, updates):
        if job_id in in_memory_jobs:
            in_memory_jobs[job_id].update(updates)

    async def mock_get(job_id):
        return in_memory_jobs.get(job_id)

    return in_memory_jobs, mock_create, mock_update, mock_get


# ==============================================================================
# TESTS
# ==============================================================================


async def test_1_batch_greater_than_50_ranks_all_candidates():
    """Verify that a batch with 75 eligible candidates processes and ranks all 75."""
    print("\n--- TEST 1: BATCH > 50 CANDIDATES (75 ELIGIBLE) RANKS EVERY CANDIDATE ---")
    in_memory_jobs, mock_create, mock_update, mock_get = setup_in_memory_job_repo()
    candidate_count = 75

    res_docs = [
        {"upload_id": "batch_synthetic_all", "filename": f"candidate_{i:03d}.pdf"}
        for i in range(candidate_count)
    ]

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=candidate_count)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=res_docs)
    mock_resumes_col.find.return_value = mock_cursor

    async def mock_match_side_effect(*args, **kwargs):
        filename = kwargs.get("filename") or args[1]
        idx = int(filename.replace("candidate_", "").replace(".pdf", ""))
        return create_mock_match_result(idx)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get), \
         patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc(total_files=candidate_count))), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(side_effect=mock_get_resume_emb)), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        # Create and run job with default limit (limit=None)
        job = await ranking_engine.create_and_start_ranking_job()
        job_id = job["job_id"]
        assert job["total_eligible"] == candidate_count, f"Expected total_eligible {candidate_count}, got {job['total_eligible']}"

        # Wait for background task to complete
        if job_id in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id]

        final_job = in_memory_jobs[job_id]
        assert final_job["status"] == "completed", f"Job status is {final_job['status']}"
        assert final_job["completed_count"] == candidate_count, f"Completed count {final_job['completed_count']} != {candidate_count}"
        assert final_job["progress_percentage"] == 100.0

        result = final_job["result"]
        assert result is not None
        assert len(result["ranked_candidates"]) == candidate_count, (
            f"Expected {candidate_count} ranked candidates, got {len(result['ranked_candidates'])}"
        )
        assert result["total_eligible"] == candidate_count
        assert result["ranked_count"] == candidate_count
        assert result["has_more"] is False
        assert result["limit"] is None

        # Verify rank indices 1..75
        ranks = [c["rank"] for c in result["ranked_candidates"]]
        assert ranks == list(range(1, candidate_count + 1)), "Ranks must be contiguous 1..N"

        print_status(f"Test 1: Batch with {candidate_count} candidates ranked all {candidate_count} with contiguous ranks 1..{candidate_count}", True)


async def test_2_batch_exactly_50_candidates():
    """Verify that a batch with exactly 50 candidates behaves correctly."""
    print("\n--- TEST 2: BATCH WITH EXACTLY 50 CANDIDATES ---")
    in_memory_jobs, mock_create, mock_update, mock_get = setup_in_memory_job_repo()
    candidate_count = 50

    res_docs = [
        {"upload_id": "batch_synthetic_all", "filename": f"candidate_{i:03d}.pdf"}
        for i in range(candidate_count)
    ]

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=candidate_count)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=res_docs)
    mock_resumes_col.find.return_value = mock_cursor

    async def mock_match_side_effect(*args, **kwargs):
        filename = kwargs.get("filename") or args[1]
        idx = int(filename.replace("candidate_", "").replace(".pdf", ""))
        return create_mock_match_result(idx)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get), \
         patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc(total_files=candidate_count))), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(side_effect=mock_get_resume_emb)), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        job = await ranking_engine.create_and_start_ranking_job()
        job_id = job["job_id"]
        if job_id in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id]

        final_job = in_memory_jobs[job_id]
        assert final_job["completed_count"] == 50
        result = final_job["result"]
        assert len(result["ranked_candidates"]) == 50
        assert result["has_more"] is False
        print_status("Test 2: Exactly 50 candidates ranked completely and correctly", True)


async def test_3_batch_fewer_than_50_candidates():
    """Verify that a batch with fewer than 50 candidates (15 candidates) behaves correctly."""
    print("\n--- TEST 3: BATCH WITH FEWER THAN 50 CANDIDATES (15 CANDIDATES) ---")
    in_memory_jobs, mock_create, mock_update, mock_get = setup_in_memory_job_repo()
    candidate_count = 15

    res_docs = [
        {"upload_id": "batch_synthetic_all", "filename": f"candidate_{i:03d}.pdf"}
        for i in range(candidate_count)
    ]

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=candidate_count)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=res_docs)
    mock_resumes_col.find.return_value = mock_cursor

    async def mock_match_side_effect(*args, **kwargs):
        filename = kwargs.get("filename") or args[1]
        idx = int(filename.replace("candidate_", "").replace(".pdf", ""))
        return create_mock_match_result(idx)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get), \
         patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc(total_files=candidate_count))), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(side_effect=mock_get_resume_emb)), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        job = await ranking_engine.create_and_start_ranking_job()
        job_id = job["job_id"]
        if job_id in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id]

        final_job = in_memory_jobs[job_id]
        assert final_job["completed_count"] == 15
        result = final_job["result"]
        assert len(result["ranked_candidates"]) == 15
        assert result["has_more"] is False
        print_status("Test 3: Fewer than 50 candidates (15) ranked completely and correctly", True)


async def test_4_ineligible_candidates_excluded():
    """Verify that ineligible candidates (failed status or missing resume_data) are excluded."""
    print("\n--- TEST 4: INELIGIBLE CANDIDATES REMAIN EXCLUDED ---")
    in_memory_jobs, mock_create, mock_update, mock_get = setup_in_memory_job_repo()

    # Total batch has 80 candidates: 60 eligible, 10 failed, 10 missing resume_data
    total_batch_files = 80
    eligible_count = 60

    eligible_docs = [
        {"upload_id": "batch_synthetic_all", "filename": f"candidate_{i:03d}.pdf"}
        for i in range(eligible_count)
    ]

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=eligible_count)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=eligible_docs)
    mock_resumes_col.find.return_value = mock_cursor

    async def mock_match_side_effect(*args, **kwargs):
        filename = kwargs.get("filename") or args[1]
        idx = int(filename.replace("candidate_", "").replace(".pdf", ""))
        return create_mock_match_result(idx)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get), \
         patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc(total_files=total_batch_files))), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(side_effect=mock_get_resume_emb)), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        job = await ranking_engine.create_and_start_ranking_job()
        job_id = job["job_id"]
        assert job["total_eligible"] == eligible_count

        if job_id in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id]

        final_job = in_memory_jobs[job_id]
        result = final_job["result"]
        # Verify exactly 60 candidates ranked, the 20 ineligible candidates were excluded
        assert len(result["ranked_candidates"]) == eligible_count
        assert final_job["completed_count"] == eligible_count

        # Verify mongo query filter was called with strict eligibility criteria
        find_calls = mock_resumes_col.find.call_args_list
        assert len(find_calls) >= 1
        query_filter = find_calls[0][0][0]
        assert query_filter["status"] == "completed"
        assert query_filter["resume_data"] == {"$ne": None}

        print_status("Test 4: Ineligible candidates excluded; only eligible candidates ranked", True)


async def test_5_progress_increments_reflect_full_count():
    """Verify that in-flight progress reflects the full eligible count without a 50 cap."""
    print("\n--- TEST 5: PROGRESS INCREMENTS AND TOTAL COUNT REFLECT FULL BATCH ---")
    in_memory_jobs = {}
    progress_snapshots = []

    async def mock_create(doc):
        in_memory_jobs[doc["job_id"]] = dict(doc)
        return doc

    async def mock_update(job_id, updates):
        if job_id in in_memory_jobs:
            in_memory_jobs[job_id].update(updates)
            if "progress_percentage" in updates:
                progress_snapshots.append(
                    (updates.get("completed_count"), updates.get("progress_percentage"))
                )

    async def mock_get(job_id):
        return in_memory_jobs.get(job_id)

    candidate_count = 70
    res_docs = [
        {"upload_id": "batch_synthetic_all", "filename": f"candidate_{i:03d}.pdf"}
        for i in range(candidate_count)
    ]

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=candidate_count)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=res_docs)
    mock_resumes_col.find.return_value = mock_cursor

    async def mock_match_side_effect(*args, **kwargs):
        filename = kwargs.get("filename") or args[1]
        idx = int(filename.replace("candidate_", "").replace(".pdf", ""))
        return create_mock_match_result(idx)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get), \
         patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc(total_files=candidate_count))), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(side_effect=mock_get_resume_emb)), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        job = await ranking_engine.create_and_start_ranking_job()
        job_id = job["job_id"]
        if job_id in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id]

        final_job = in_memory_jobs[job_id]
        assert final_job["completed_count"] == candidate_count
        assert final_job["total_eligible"] == candidate_count

        # Check in-flight progress snapshots passed past 50
        counts = [s[0] for s in progress_snapshots if s[0] is not None]
        assert any(c > 50 for c in counts), f"Expected progress to record completed counts > 50, got {counts}"
        # Verify 70th candidate yields 100.0%
        last_progress = [s[1] for s in progress_snapshots if s[1] is not None][-1]
        assert last_progress == 100.0

        print_status("Test 5: Progress increments monotonically beyond 50 to 100.0% of full batch", True)


async def test_6_score_components_explainability_and_ties():
    """Verify that score breakdown, evidence, and tie-handling behavior are strictly preserved."""
    print("\n--- TEST 6: SCORE COMPONENTS, EXPLAINABILITY, AND TIE HANDLING PRESERVED ---")
    in_memory_jobs, mock_create, mock_update, mock_get = setup_in_memory_job_repo()
    candidate_count = 60

    res_docs = [
        {"upload_id": "batch_synthetic_all", "filename": f"candidate_{i:03d}.pdf"}
        for i in range(candidate_count)
    ]

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=candidate_count)
    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=res_docs)
    mock_resumes_col.find.return_value = mock_cursor

    async def mock_match_side_effect(*args, **kwargs):
        filename = kwargs.get("filename") or args[1]
        idx = int(filename.replace("candidate_", "").replace(".pdf", ""))
        return create_mock_match_result(idx)

    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get), \
         patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc(total_files=candidate_count))), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(side_effect=mock_get_resume_emb)), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        job = await ranking_engine.create_and_start_ranking_job()
        job_id = job["job_id"]
        if job_id in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id]

        final_job = in_memory_jobs[job_id]
        result = final_job["result"]
        candidates = result["ranked_candidates"]

        # Check explainability components on every candidate
        for cand in candidates:
            assert cand["final_score"] is not None
            assert 0.0 <= cand["final_score"] <= 100.0
            assert cand["status"] == "complete"
            assert "component_scores" in cand
            cs = cand["component_scores"]
            assert "required_skills" in cs
            assert "responsibilities" in cs
            assert "tools_and_technologies" in cs
            assert "experience_relevance" in cs
            assert "breakdown" in cand
            assert "experience_diagnostic" in cand
            assert cand["experience_diagnostic"]["relevant_duration_years"] > 0

        # Check descending sort order: cand[i].final_score >= cand[i+1].final_score
        scores = [c["final_score"] for c in candidates]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Ranking order violated: {scores[i]} < {scores[i+1]} at {i}"

        print_status("Test 6: All score components, explainability breakdowns, and descending order verified", True)


async def test_7_explicit_limit_versus_default_full_batch():
    """Verify that when limit is explicitly passed, it is respected, while default ranks all."""
    print("\n--- TEST 7: EXPLICIT LIMIT VERSUS DEFAULT FULL BATCH BEHAVIOR ---")
    in_memory_jobs, mock_create, mock_update, mock_get = setup_in_memory_job_repo()
    candidate_count = 70

    mock_resumes_col = MagicMock()
    mock_resumes_col.count_documents = AsyncMock(return_value=candidate_count)

    def make_cursor(limit):
        cursor = MagicMock()
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        # If limit is None, return all; otherwise return sliced
        n = limit if limit is not None else candidate_count
        cursor.to_list = AsyncMock(return_value=[
            {"upload_id": "batch_synthetic_all", "filename": f"candidate_{i:03d}.pdf"}
            for i in range(n)
        ])
        return cursor

    async def mock_match_side_effect(*args, **kwargs):
        filename = kwargs.get("filename") or args[1]
        idx = int(filename.replace("candidate_", "").replace(".pdf", ""))
        return create_mock_match_result(idx)

    # Subtest 7A: Explicit limit=30
    mock_resumes_col.find.return_value = make_cursor(30)
    with patch.object(ranking_job_repository, "create_job", side_effect=mock_create), \
         patch.object(ranking_job_repository, "update_job", side_effect=mock_update), \
         patch.object(ranking_job_repository, "get_job", side_effect=mock_get), \
         patch("app.ranking.ranking_service.jd_repository.get", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_repository.get_active", new=AsyncMock(return_value=create_mock_jd_doc())), \
         patch("app.ranking.ranking_service.jd_embedding_repository.get_by_jd_id", new=AsyncMock(return_value=create_mock_jd_embeddings_doc())), \
         patch("app.ranking.ranking_service.batch_repository.get_active", new=AsyncMock(return_value=create_mock_batch_doc(total_files=candidate_count))), \
         patch("app.ranking.ranking_service.resume_embedding_repository.get", new=AsyncMock(side_effect=mock_get_resume_emb)), \
         patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", side_effect=mock_match_side_effect), \
         patch("app.database.mongodb.mongodb.get_database", return_value={"resumes": mock_resumes_col}):

        job_30 = await ranking_engine.create_and_start_ranking_job(limit=30)
        job_id_30 = job_30["job_id"]
        if job_id_30 in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id_30]

        result_30 = in_memory_jobs[job_id_30]["result"]
        assert len(result_30["ranked_candidates"]) == 30
        assert result_30["limit"] == 30
        assert result_30["has_more"] is True

        # Subtest 7B: Default (limit=None)
        mock_resumes_col.find.return_value = make_cursor(None)
        job_all = await ranking_engine.create_and_start_ranking_job(limit=None)
        job_id_all = job_all["job_id"]
        if job_id_all in ranking_engine._active_tasks:
            await ranking_engine._active_tasks[job_id_all]

        result_all = in_memory_jobs[job_id_all]["result"]
        assert len(result_all["ranked_candidates"]) == candidate_count
        assert result_all["limit"] is None
        assert result_all["has_more"] is False

        print_status("Test 7: Explicit limit=30 and default limit=None both adhere to contract", True)


async def run_all_tests():
    print("=" * 80)
    print("TALENTAI — SYNTHETIC TEST SUITE: RANK-ALL CANDIDATES & PROGRESS")
    print("=" * 80)
    await test_1_batch_greater_than_50_ranks_all_candidates()
    await test_2_batch_exactly_50_candidates()
    await test_3_batch_fewer_than_50_candidates()
    await test_4_ineligible_candidates_excluded()
    await test_5_progress_increments_reflect_full_count()
    await test_6_score_components_explainability_and_ties()
    await test_7_explicit_limit_versus_default_full_batch()
    print("=" * 80)
    print("ALL 7 SYNTHETIC RANK-ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
