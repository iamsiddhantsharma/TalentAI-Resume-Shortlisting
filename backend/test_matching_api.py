"""
TalentAI — Phase 5.8: Matching API Regression Test Suite

Verifies:
1. Single-resume matching succeeds (POST /matching/match-resume)
2. Missing resume returns HTTP 404
3. Missing resume embeddings returns HTTP 404
4. Missing active JD returns HTTP 404
5. Missing active JD embeddings returns HTTP 404
6. Invalid request data returns HTTP 422
7. Match-all processes multiple eligible resumes (POST /matching/match-all)
8. Match-all reports individual candidate failures correctly without failing batch
9. Empty resume collections are handled safely
10. Matching outputs preserve provenance and separate semantic retrieval sections
11. API responses contain NO invented ranking/scoring fields (Phase 6 boundary)
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app

client = TestClient(app)


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


SAMPLE_MATCH_RESULT = {
    "jd_id": "jd_active_123",
    "upload_id": "upload_abc_456",
    "filename": "alice.pdf",
    "exact_matching": {
        "total_required_skills": 2,
        "matched_required_skills": 2,
        "unmatched_required_skills": 0,
        "matches": [
            {
                "required_skill": "Python",
                "matched": True,
                "resume_skill": "Python",
                "match_type": "exact_normalized",
            },
            {
                "required_skill": "FastAPI",
                "matched": True,
                "resume_skill": "FastAPI",
                "match_type": "exact_normalized",
            },
        ],
    },
    "semantic_retrieval": {
        "top_k": 5,
        "responsibilities_retrieval": {
            "top_k": 5,
            "results": [
                {
                    "jd_section": "responsibilities",
                    "jd_item_index": 0,
                    "jd_text": "Responsibility: Build scalable microservices",
                    "matches": [
                        {
                            "jd_section": "responsibilities",
                            "jd_item_index": 0,
                            "jd_text": "Responsibility: Build scalable microservices",
                            "resume_section": "projects",
                            "resume_item_index": 0,
                            "resume_text": "Project: Cloud Microservices in FastAPI",
                            "similarity": 0.88,
                        }
                    ],
                }
            ],
        },
        "tools_and_technologies_retrieval": {
            "top_k": 5,
            "results": [
                {
                    "jd_section": "tools_and_technologies",
                    "jd_item_index": 0,
                    "jd_text": "Tool: Docker",
                    "matches": [
                        {
                            "jd_section": "tools_and_technologies",
                            "jd_item_index": 0,
                            "jd_text": "Tool: Docker",
                            "resume_section": "projects",
                            "resume_item_index": 0,
                            "resume_text": "Project: Dockerized App",
                            "similarity": 0.91,
                        }
                    ],
                }
            ],
        },
        "results": [
            {
                "jd_section": "responsibilities",
                "jd_item_index": 0,
                "jd_text": "Responsibility: Build scalable microservices",
                "matches": [
                    {
                        "jd_section": "responsibilities",
                        "jd_item_index": 0,
                        "jd_text": "Responsibility: Build scalable microservices",
                        "resume_section": "projects",
                        "resume_item_index": 0,
                        "resume_text": "Project: Cloud Microservices in FastAPI",
                        "similarity": 0.88,
                    }
                ],
            },
            {
                "jd_section": "tools_and_technologies",
                "jd_item_index": 0,
                "jd_text": "Tool: Docker",
                "matches": [
                    {
                        "jd_section": "tools_and_technologies",
                        "jd_item_index": 0,
                        "jd_text": "Tool: Docker",
                        "resume_section": "projects",
                        "resume_item_index": 0,
                        "resume_text": "Project: Dockerized App",
                        "similarity": 0.91,
                    }
                ],
            },
        ],
    },
    "experience_matching": {
        "experience_requirements": {
            "minimum_years": 2.0,
            "maximum_years": 5.0,
            "preferred_domains": ["Backend"],
        },
        "experience_requirement_present": True,
        "experiences": [
            {
                "experience_index": 0,
                "role": "Backend Developer",
                "company": "Acme Corp",
                "description": "Developed backend APIs",
                "decision": "RELEVANT",
                "relevant": True,
                "duration_years": 2.5,
                "duration_available": True,
                "start_date": "2021-01",
                "end_date": "2023-07",
            }
        ],
        "relevant_experience_found": True,
        "relevant_duration_years": 2.5,
        "minimum_years": 2.0,
        "maximum_years": 5.0,
        "minimum_duration_satisfied": True,
        "maximum_duration_exceeded": False,
    },
}


# ==============================================================================
# TEST 1: Single-resume matching succeeds
# ==============================================================================


def test_1_single_resume_matching_succeeds():
    print("\n" + "=" * 70)
    print("TEST 1: SINGLE-RESUME MATCHING SUCCEEDS")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123", "status": "completed"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}
    mock_resume = {
        "_id": "upload_abc_456:alice.pdf",
        "upload_id": "upload_abc_456",
        "filename": "alice.pdf",
        "status": "completed",
        "resume_data": {"name": "Alice"},
    }
    mock_resume_emb = {
        "_id": "upload_abc_456:alice.pdf",
        "upload_id": "upload_abc_456",
        "filename": "alice.pdf",
        "embeddings": [{}],
    }

    mock_batch = {
        "_id": "upload_abc_456",
        "batch_id": "upload_abc_456",
        "status": "active",
        "is_active": True,
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.resume_repository.get", new_callable=AsyncMock) as mock_get_resume,
        patch("app.api.matching.resume_embedding_repository.get", new_callable=AsyncMock) as mock_get_res_emb,
        patch("app.api.matching.hybrid_matching_service.match_resume", new_callable=AsyncMock) as mock_match,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch
        mock_get_resume.return_value = mock_resume
        mock_get_res_emb.return_value = mock_resume_emb
        mock_match.return_value = SAMPLE_MATCH_RESULT

        response = client.post(
            "/matching/match-resume",
            json={"upload_id": "upload_abc_456", "filename": "alice.pdf"},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["upload_id"] == "upload_abc_456"
        assert data["filename"] == "alice.pdf"
        assert data["jd_id"] == "jd_active_123"
        assert "exact_matching" in data
        assert "semantic_retrieval" in data
        assert "experience_matching" in data

    print_status("Single-resume matching succeeds (HTTP 200)", True)


# ==============================================================================
# TEST 2: Missing resume returns 404
# ==============================================================================


def test_2_missing_resume_returns_404():
    print("\n" + "=" * 70)
    print("TEST 2: MISSING RESUME RETURNS 404")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}

    mock_batch = {
        "_id": "nonexistent_upload",
        "batch_id": "nonexistent_upload",
        "status": "active",
        "is_active": True,
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.resume_repository.get", new_callable=AsyncMock) as mock_get_resume,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch
        mock_get_resume.return_value = None  # Resume does not exist

        response = client.post(
            "/matching/match-resume",
            json={"upload_id": "nonexistent_upload", "filename": "ghost.pdf"},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "Resume not found" in response.json()["detail"]

    print_status("Missing resume returns HTTP 404", True)


# ==============================================================================
# TEST 3: Missing resume embeddings returns 404
# ==============================================================================


def test_3_missing_resume_embeddings_returns_404():
    print("\n" + "=" * 70)
    print("TEST 3: MISSING RESUME EMBEDDINGS RETURNS 404")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}
    mock_resume = {
        "_id": "upload_1:test.pdf",
        "upload_id": "upload_1",
        "filename": "test.pdf",
        "status": "completed",
        "resume_data": {"name": "Test"},
    }

    mock_batch = {
        "_id": "upload_1",
        "batch_id": "upload_1",
        "status": "active",
        "is_active": True,
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.resume_repository.get", new_callable=AsyncMock) as mock_get_resume,
        patch("app.api.matching.resume_embedding_repository.get", new_callable=AsyncMock) as mock_get_res_emb,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch
        mock_get_resume.return_value = mock_resume
        mock_get_res_emb.return_value = None  # Embeddings missing

        response = client.post(
            "/matching/match-resume",
            json={"upload_id": "upload_1", "filename": "test.pdf"},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "Embeddings not found for resume" in response.json()["detail"]

    print_status("Missing resume embeddings returns HTTP 404", True)


# ==============================================================================
# TEST 4: Missing active JD returns 404
# ==============================================================================


def test_4_missing_active_jd_returns_404():
    print("\n" + "=" * 70)
    print("TEST 4: MISSING ACTIVE JD RETURNS 404")
    print("=" * 70)

    with patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd:
        mock_get_active_jd.return_value = None  # No active JD in DB

        response = client.post(
            "/matching/match-resume",
            json={"upload_id": "upload_1", "filename": "test.pdf"},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "No active job description found" in response.json()["detail"]

    print_status("Missing active JD returns HTTP 404", True)


# ==============================================================================
# TEST 5: Missing active JD embeddings returns 404
# ==============================================================================


def test_5_missing_active_jd_embeddings_returns_404():
    print("\n" + "=" * 70)
    print("TEST 5: MISSING ACTIVE JD EMBEDDINGS RETURNS 404")
    print("=" * 70)

    mock_jd = {"_id": "jd_no_emb", "jd_id": "jd_no_emb"}

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = None  # JD embeddings missing

        response = client.post(
            "/matching/match-resume",
            json={"upload_id": "upload_1", "filename": "test.pdf"},
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "Embeddings not found for active job description" in response.json()["detail"]

    print_status("Missing active JD embeddings returns HTTP 404", True)


# ==============================================================================
# TEST 6: Invalid request data returns 422
# ==============================================================================


def test_6_invalid_request_data_returns_422():
    print("\n" + "=" * 70)
    print("TEST 6: INVALID REQUEST DATA RETURNS 422")
    print("=" * 70)

    # Missing filename
    res1 = client.post("/matching/match-resume", json={"upload_id": "up_1"})
    assert res1.status_code == 422, f"Expected 422 for missing filename, got {res1.status_code}"

    # Missing upload_id
    res2 = client.post("/matching/match-resume", json={"filename": "test.pdf"})
    assert res2.status_code == 422, f"Expected 422 for missing upload_id, got {res2.status_code}"

    # Extra forbidden fields (due to extra='forbid')
    res3 = client.post(
        "/matching/match-resume",
        json={"upload_id": "up_1", "filename": "test.pdf", "invented_score": 95},
    )
    assert res3.status_code == 422, f"Expected 422 for extra forbidden field, got {res3.status_code}"

    # Invalid pagination in match-all (limit < 1)
    res4 = client.post("/matching/match-all", json={"limit": 0})
    assert res4.status_code == 422, f"Expected 422 for limit=0, got {res4.status_code}"

    # Invalid pagination in match-all (limit > 100)
    res5 = client.post("/matching/match-all", json={"limit": 101})
    assert res5.status_code == 422, f"Expected 422 for limit=101, got {res5.status_code}"

    print_status("Invalid request schemas return HTTP 422", True)


# ==============================================================================
# TEST 7: Match-all processes multiple eligible resumes
# ==============================================================================


def test_7_match_all_processes_multiple_resumes():
    print("\n" + "=" * 70)
    print("TEST 7: MATCH-ALL PROCESSES MULTIPLE ELIGIBLE RESUMES")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}

    mock_batch = {
        "_id": "up_batch_1",
        "batch_id": "up_batch_1",
        "status": "active",
        "is_active": True,
    }

    eligible_resumes = [
        {"upload_id": "up_batch_1", "filename": "cand1.pdf"},
        {"upload_id": "up_batch_1", "filename": "cand2.pdf"},
    ]

    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=eligible_resumes)

    mock_collection = MagicMock()
    mock_collection.count_documents = AsyncMock(return_value=2)
    mock_collection.find.return_value = mock_cursor

    mock_db = {"resumes": mock_collection}

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.mongodb.get_database", return_value=mock_db),
        patch("app.api.matching.resume_embedding_repository.get", new_callable=AsyncMock) as mock_get_res_emb,
        patch("app.api.matching.hybrid_matching_service.match_resume", new_callable=AsyncMock) as mock_match,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch
        mock_get_res_emb.return_value = {"embeddings": [{}]}
        mock_match.return_value = SAMPLE_MATCH_RESULT

        response = client.post("/matching/match-all", json={"limit": 50, "skip": 0})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["jd_id"] == "jd_active_123"
        assert data["total_eligible_resumes"] == 2
        assert data["processed_count"] == 2
        assert data["successful_count"] == 2
        assert data["failed_count"] == 0
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "completed"
        assert data["results"][1]["status"] == "completed"
        assert data["results"][0]["upload_id"] == "up_batch_1"
        assert data["results"][1]["upload_id"] == "up_batch_1"

    print_status("Match-all processes multiple candidates (HTTP 200)", True)


# ==============================================================================
# TEST 8: Match-all reports individual candidate failures correctly
# ==============================================================================


def test_8_match_all_reports_individual_failures():
    print("\n" + "=" * 70)
    print("TEST 8: MATCH-ALL REPORTS INDIVIDUAL FAILURES SAFELY")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}

    mock_batch = {
        "_id": "up_batch_1",
        "batch_id": "up_batch_1",
        "status": "active",
        "is_active": True,
    }

    eligible_resumes = [
        {"upload_id": "up_batch_1", "filename": "good.pdf"},
        {"upload_id": "up_batch_1", "filename": "no_emb.pdf"},
    ]

    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=eligible_resumes)

    mock_collection = MagicMock()
    mock_collection.count_documents = AsyncMock(return_value=2)
    mock_collection.find.return_value = mock_cursor

    mock_db = {"resumes": mock_collection}

    async def fake_get_res_emb(upload_id, filename):
        if filename == "good.pdf":
            return {"embeddings": [{}]}
        return None  # no_emb has no embeddings

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.mongodb.get_database", return_value=mock_db),
        patch("app.api.matching.resume_embedding_repository.get", side_effect=fake_get_res_emb),
        patch("app.api.matching.hybrid_matching_service.match_resume", new_callable=AsyncMock) as mock_match,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch
        mock_match.return_value = SAMPLE_MATCH_RESULT

        response = client.post("/matching/match-all", json={"limit": 50, "skip": 0})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["total_eligible_resumes"] == 2
        assert data["processed_count"] == 2
        assert data["successful_count"] == 1
        assert data["failed_count"] == 1

        results = data["results"]
        assert results[0]["upload_id"] == "up_batch_1"
        assert results[0]["status"] == "completed"
        assert results[0]["error"] is None
        assert results[0]["match"] is not None

        assert results[1]["upload_id"] == "up_batch_1"
        assert results[1]["status"] == "failed"
        assert "Embeddings not found" in results[1]["error"]
        assert results[1]["match"] is None

    print_status("Match-all reports candidate failures without crashing batch", True)


# ==============================================================================
# TEST 9: Empty resume collections are handled safely
# ==============================================================================


def test_9_empty_resume_collections_handled_safely():
    print("\n" + "=" * 70)
    print("TEST 9: EMPTY RESUME COLLECTIONS HANDLED SAFELY")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}

    mock_batch = {
        "_id": "up_batch_1",
        "batch_id": "up_batch_1",
        "status": "active",
        "is_active": True,
    }

    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[])

    mock_collection = MagicMock()
    mock_collection.count_documents = AsyncMock(return_value=0)
    mock_collection.find.return_value = mock_cursor

    mock_db = {"resumes": mock_collection}

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.mongodb.get_database", return_value=mock_db),
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch

        response = client.post("/matching/match-all", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["total_eligible_resumes"] == 0
        assert data["processed_count"] == 0
        assert data["successful_count"] == 0
        assert data["failed_count"] == 0
        assert data["results"] == []

    print_status("Empty resume collection returns empty batch safely", True)


# ==============================================================================
# TEST 10: Provenance and section separation preserved
# ==============================================================================


def test_10_provenance_and_separation_preserved():
    print("\n" + "=" * 70)
    print("TEST 10: PROVENANCE AND SEPARATION PRESERVED")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}
    mock_resume = {
        "_id": "up:f.pdf",
        "upload_id": "up",
        "filename": "f.pdf",
        "status": "completed",
        "resume_data": {"name": "Test"},
    }
    mock_resume_emb = {"_id": "up:f.pdf", "upload_id": "up", "filename": "f.pdf", "embeddings": [{}]}

    mock_batch = {
        "_id": "up",
        "batch_id": "up",
        "status": "active",
        "is_active": True,
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.resume_repository.get", new_callable=AsyncMock) as mock_get_resume,
        patch("app.api.matching.resume_embedding_repository.get", new_callable=AsyncMock) as mock_get_res_emb,
        patch("app.api.matching.hybrid_matching_service.match_resume", new_callable=AsyncMock) as mock_match,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch
        mock_get_resume.return_value = mock_resume
        mock_get_res_emb.return_value = mock_resume_emb
        mock_match.return_value = SAMPLE_MATCH_RESULT

        response = client.post("/matching/match-resume", json={"upload_id": "up", "filename": "f.pdf"})
        data = response.json()

        sr = data["semantic_retrieval"]
        assert "responsibilities_retrieval" in sr
        assert "tools_and_technologies_retrieval" in sr

        # Verify responsibility match provenance
        resp_matches = sr["responsibilities_retrieval"]["results"][0]["matches"]
        assert len(resp_matches) > 0
        m = resp_matches[0]
        assert m["jd_section"] == "responsibilities"
        assert m["resume_section"] == "projects"
        assert m["jd_item_index"] == 0
        assert m["resume_item_index"] == 0
        assert "similarity" in m
        assert m["similarity"] == 0.88

        # Verify tools match provenance
        tool_matches = sr["tools_and_technologies_retrieval"]["results"][0]["matches"]
        assert len(tool_matches) > 0
        tm = tool_matches[0]
        assert tm["jd_section"] == "tools_and_technologies"
        assert tm["resume_section"] == "projects"
        assert tm["similarity"] == 0.91

    print_status("Full provenance and section separation preserved", True)


# ==============================================================================
# TEST 11: API responses contain NO invented ranking fields (Phase 6 boundary)
# ==============================================================================


def test_11_no_invented_ranking_fields():
    print("\n" + "=" * 70)
    print("TEST 11: STRICT ARCHITECTURAL BOUNDARY — NO RANKING FIELDS")
    print("=" * 70)

    forbidden_keywords = [
        "score",
        "rank",
        "ranking",
        "shortlist",
        "weight",
        "weighted_score",
        "hire",
        "pass_fail",
        "final_score",
        "candidate_score",
    ]

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}
    mock_resume = {
        "_id": "up:f.pdf",
        "upload_id": "up",
        "filename": "f.pdf",
        "status": "completed",
        "resume_data": {"name": "Test"},
    }
    mock_resume_emb = {"_id": "up:f.pdf", "upload_id": "up", "filename": "f.pdf", "embeddings": [{}]}

    mock_batch = {
        "_id": "up",
        "batch_id": "up",
        "status": "active",
        "is_active": True,
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_batch,
        patch("app.api.matching.resume_repository.get", new_callable=AsyncMock) as mock_get_resume,
        patch("app.api.matching.resume_embedding_repository.get", new_callable=AsyncMock) as mock_get_res_emb,
        patch("app.api.matching.hybrid_matching_service.match_resume", new_callable=AsyncMock) as mock_match,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_batch.return_value = mock_batch
        mock_get_resume.return_value = mock_resume
        mock_get_res_emb.return_value = mock_resume_emb
        mock_match.return_value = SAMPLE_MATCH_RESULT

        response = client.post("/matching/match-resume", json={"upload_id": "up", "filename": "f.pdf"})
        data = response.json()

        def scan_keys(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    # "decision" is allowed within experience decisions (RELEVANT/IRRELEVANT),
                    # but overall hiring/shortlisting decisions are forbidden.
                    for fk in forbidden_keywords:
                        if fk == k.lower() and k != "decision":
                            assert False, f"Forbidden ranking/scoring key found: '{path}.{k}'"
                    scan_keys(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, elem in enumerate(obj):
                    scan_keys(elem, f"{path}[{i}]")

        scan_keys(data)

    print_status("Zero ranking, scoring, or shortlist fields present (Phase 6 boundary enforced)", True)


# ==============================================================================
# TEST 12: Match-resume rejects resume belonging to inactive batch
# ==============================================================================


def test_12_match_resume_rejects_inactive_batch():
    print("\n" + "=" * 70)
    print("TEST 12: MATCH-RESUME REJECTS INACTIVE BATCH")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}

    # Current active batch is batch_2
    mock_active_batch = {
        "_id": "batch_2",
        "batch_id": "batch_2",
        "status": "active",
        "is_active": True,
    }
    # Candidate requested is from batch_1 (superseded)
    mock_superseded_batch = {
        "_id": "batch_1",
        "batch_id": "batch_1",
        "status": "superseded",
        "is_active": False,
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_b,
        patch("app.api.matching.batch_repository.get", new_callable=AsyncMock) as mock_get_b,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_b.return_value = mock_active_batch
        mock_get_b.return_value = mock_superseded_batch

        response = client.post(
            "/matching/match-resume",
            json={"upload_id": "batch_1", "filename": "alice.pdf"},
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "not the active candidate batch" in response.json()["detail"]

    print_status("Match-resume rejects candidate from inactive batch (HTTP 400)", True)


# ==============================================================================
# TEST 13: Match-all rejects request specifying inactive batch
# ==============================================================================


def test_13_match_all_rejects_inactive_batch():
    print("\n" + "=" * 70)
    print("TEST 13: MATCH-ALL REJECTS INACTIVE BATCH SPECIFICATION")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}

    mock_active_batch = {
        "_id": "batch_2",
        "batch_id": "batch_2",
        "status": "active",
        "is_active": True,
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_b,
        patch("app.api.matching.batch_repository.get", new_callable=AsyncMock) as mock_get_b,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_b.return_value = mock_active_batch
        mock_get_b.return_value = {"status": "superseded"}

        response = client.post(
            "/matching/match-all",
            json={"upload_id": "batch_old_1"},
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "not the active candidate batch" in response.json()["detail"]

    print_status("Match-all rejects inactive batch filter (HTTP 400)", True)


# ==============================================================================
# TEST 14: Match-all requires an active batch
# ==============================================================================


def test_14_match_all_requires_active_batch():
    print("\n" + "=" * 70)
    print("TEST 14: MATCH-ALL REQUIRES AN ACTIVE BATCH")
    print("=" * 70)

    mock_jd = {"_id": "jd_active_123", "jd_id": "jd_active_123"}
    mock_jd_emb = {"_id": "active_jd", "jd_id": "jd_active_123", "embeddings": [{}]}

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as mock_get_active_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as mock_get_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as mock_get_active_b,
    ):
        mock_get_active_jd.return_value = mock_jd
        mock_get_jd_emb.return_value = mock_jd_emb
        mock_get_active_b.return_value = None  # No batch active

        response = client.post(
            "/matching/match-all",
            json={},
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "No active recruitment batch found" in response.json()["detail"]

    print_status("Match-all returns HTTP 400 when no batch is active", True)


# ==============================================================================
# MAIN RUNNER
# ==============================================================================


def main():
    print("=" * 80)
    print("TALENTAI — PHASE 5 MATCHING API & BATCH ISOLATION TEST SUITE")
    print("=" * 80)

    test_1_single_resume_matching_succeeds()
    test_2_missing_resume_returns_404()
    test_3_missing_resume_embeddings_returns_404()
    test_4_missing_active_jd_returns_404()
    test_5_missing_active_jd_embeddings_returns_404()
    test_6_invalid_request_data_returns_422()
    test_7_match_all_processes_multiple_resumes()
    test_8_match_all_reports_individual_failures()
    test_9_empty_resume_collections_handled_safely()
    test_10_provenance_and_separation_preserved()
    test_11_no_invented_ranking_fields()
    test_12_match_resume_rejects_inactive_batch()
    test_13_match_all_rejects_inactive_batch()
    test_14_match_all_requires_active_batch()

    print("\n" + "=" * 80)
    print("ALL API TESTS (1 through 14) PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
