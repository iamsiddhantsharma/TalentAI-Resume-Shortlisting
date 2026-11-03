"""
TalentAI — Phase 6: Ranking API & Integration Test Suite

Tests:
E. Ranking and Integration Tests (Cases 24-30):
24. Candidates are ranked by descending final score when their results are complete.
25. Incomplete candidates are not silently ranked as zero.
26. Equal scores are handled deterministically and transparently.
27. Existing Phase 5 response keys remain intact.
28. Existing batch isolation is preserved.
29. Existing active-JD behavior is preserved.
30. Full explainable breakdown returned via single-resume ranking API.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.ranking.ranking_schemas import (
    CandidateRankingResult,
    CategoryScoreBreakdown,
    MinimumExperienceDiagnostic,
)
from app.ranking.ranking_service import ranking_engine
from app.schemas.job_description_object import ExperienceRequirement, JobDescriptionObject

client = TestClient(app)


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


SAMPLE_MATCH_PAYLOAD = {
    "jd_id": "jd_active_123",
    "upload_id": "batch_active_123",
    "filename": "alice.pdf",
    "exact_matching": {
        "total_required_skills": 2,
        "matched_required_skills": 2,
        "unmatched_required_skills": 0,
        "matches": [
            {"required_skill": "Python", "matched": True, "resume_skill": "Python", "match_type": "exact"},
            {"required_skill": "FastAPI", "matched": True, "resume_skill": "FastAPI", "match_type": "exact"},
        ],
    },
    "semantic_retrieval": {
        "top_k": 5,
        "responsibilities_retrieval": {
            "top_k": 5,
            "results": [
                {
                    "jd_item_index": 0,
                    "jd_text": "Build APIs",
                    "matches": [{"similarity": 0.85, "resume_text": "Built scalable APIs"}],
                }
            ],
        },
        "tools_and_technologies_retrieval": {
            "top_k": 5,
            "results": [
                {
                    "jd_item_index": 0,
                    "jd_text": "Docker",
                    "matches": [{"similarity": 0.80, "resume_text": "Deployed with Docker"}],
                }
            ],
        },
        "results": [],
    },
    "experience_matching": {
        "experience_requirements": {
            "minimum_years": 2.0,
            "maximum_years": 6.0,
            "preferred_domains": ["Fintech"],
        },
        "experience_requirement_present": True,
        "experiences": [
            {
                "experience_index": 0,
                "role": "Backend Engineer",
                "company": "Bank Corp",
                "description": "Payments API",
                "decision": "RELEVANT",
                "relevant": True,
                "duration_years": 3.0,
                "duration_available": True,
            }
        ],
        "relevant_experience_found": True,
        "relevant_duration_years": 3.0,
        "minimum_years": 2.0,
        "maximum_years": 6.0,
        "minimum_duration_satisfied": True,
        "maximum_duration_exceeded": False,
        "diagnostic_status": "duration_calculated",
        "diagnostic_message": "Relevant duration calculated",
    },
}

MOCK_JD_DOC = {
    "_id": "jd_active_123",
    "jd_id": "jd_active_123",
    "job_id": "jd_active_123",
    "filename": "senior_backend.txt",
    "is_active": True,
    "structured_data": {
        "required_skills": ["Python", "FastAPI"],
        "responsibilities": ["Build APIs"],
        "tools_and_technologies": ["Docker"],
        "experience_requirements": [
            {
                "minimum_years": 2.0,
                "maximum_years": 6.0,
                "preferred_domains": ["Fintech"],
            }
        ],
    },
}

MOCK_ACTIVE_BATCH = {
    "_id": "batch_active_123",
    "batch_id": "batch_active_123",
    "status": "active",
    "is_active": True,
}

MOCK_JD_EMB = {
    "_id": "emb_jd_123",
    "jd_id": "jd_active_123",
    "embeddings": [{"section": "responsibilities", "item_index": 0, "embedding": [0.1] * 1024}],
}


# ==============================================================================
# TEST 24: Candidates ranked by descending final score when complete
# ==============================================================================


def test_24_candidates_ranked_descending():
    print("\n" + "=" * 70)
    print("TEST 24: CANDIDATES RANKED BY DESCENDING FINAL SCORE")
    print("=" * 70)

    # 3 candidates with scores 92.5, 75.0, 85.0
    c1 = CandidateRankingResult(
        upload_id="b",
        filename="charlie.pdf",
        jd_id="j",
        rank=None,
        status="complete",
        final_score=75.0,
        component_scores={},
        breakdown={},
        experience_diagnostic=MinimumExperienceDiagnostic(),
    )
    c2 = CandidateRankingResult(
        upload_id="b",
        filename="alice.pdf",
        jd_id="j",
        rank=None,
        status="complete",
        final_score=92.5,
        component_scores={},
        breakdown={},
        experience_diagnostic=MinimumExperienceDiagnostic(),
    )
    c3 = CandidateRankingResult(
        upload_id="b",
        filename="bob.pdf",
        jd_id="j",
        rank=None,
        status="complete",
        final_score=85.0,
        component_scores={},
        breakdown={},
        experience_diagnostic=MinimumExperienceDiagnostic(),
    )

    ranked, unranked = ranking_engine.rank_candidates([c1, c2, c3])

    assert len(ranked) == 3
    assert len(unranked) == 0

    assert ranked[0].filename == "alice.pdf"
    assert ranked[0].final_score == 92.5
    assert ranked[0].rank == 1

    assert ranked[1].filename == "bob.pdf"
    assert ranked[1].final_score == 85.0
    assert ranked[1].rank == 2

    assert ranked[2].filename == "charlie.pdf"
    assert ranked[2].final_score == 75.0
    assert ranked[2].rank == 3

    print_status("Test 24: Candidates ordered strictly descending by final score with 1-based ranks", True)


# ==============================================================================
# TEST 25: Incomplete candidates are NOT silently ranked as zero
# ==============================================================================


def test_25_incomplete_candidates_separated_not_zero():
    print("\n" + "=" * 70)
    print("TEST 25: INCOMPLETE CANDIDATES SEPARATED AND NOT ZERO-RANKED")
    print("=" * 70)

    c_valid = CandidateRankingResult(
        upload_id="b",
        filename="valid.pdf",
        jd_id="j",
        rank=None,
        status="complete",
        final_score=80.0,
        component_scores={},
        breakdown={},
        experience_diagnostic=MinimumExperienceDiagnostic(),
    )
    c_failed = CandidateRankingResult(
        upload_id="b",
        filename="corrupted.pdf",
        jd_id="j",
        rank=None,
        status="incomplete",
        final_score=None,  # No synthetic zero!
        component_scores={},
        breakdown={},
        experience_diagnostic=MinimumExperienceDiagnostic(),
        errors=["Service unavailable"],
    )

    ranked, unranked = ranking_engine.rank_candidates([c_valid, c_failed])

    assert len(ranked) == 1
    assert ranked[0].filename == "valid.pdf"
    assert ranked[0].rank == 1

    assert len(unranked) == 1
    assert unranked[0].filename == "corrupted.pdf"
    assert unranked[0].status == "incomplete"
    assert unranked[0].final_score is None  # Must remain None, never synthetic 0.0
    assert unranked[0].rank is None

    print_status("Test 25: Incomplete candidates separated, not assigned 0.0 or included in ranked list", True)


# ==============================================================================
# TEST 26: Equal scores handled deterministically and transparently
# ==============================================================================


def test_26_equal_scores_tie_handling():
    print("\n" + "=" * 70)
    print("TEST 26: EQUAL SCORES DETERMINISTIC TIE HANDLING")
    print("=" * 70)

    # Two candidates with exactly equal score 88.50
    cA = CandidateRankingResult(
        upload_id="b",
        filename="zeta.pdf",
        jd_id="j",
        rank=None,
        status="complete",
        final_score=88.5,
        component_scores={},
        breakdown={},
        experience_diagnostic=MinimumExperienceDiagnostic(),
    )
    cB = CandidateRankingResult(
        upload_id="b",
        filename="alpha.pdf",
        jd_id="j",
        rank=None,
        status="complete",
        final_score=88.5,
        component_scores={},
        breakdown={},
        experience_diagnostic=MinimumExperienceDiagnostic(),
    )

    ranked, _ = ranking_engine.rank_candidates([cA, cB])

    assert len(ranked) == 2
    assert ranked[0].final_score == 88.5
    assert ranked[1].final_score == 88.5
    # Deterministic secondary ordering on filename ("alpha.pdf" before "zeta.pdf")
    assert ranked[0].filename == "alpha.pdf"
    assert ranked[1].filename == "zeta.pdf"

    print_status("Test 26: Identical scores ordered deterministically without modifying scores", True)


# ==============================================================================
# TEST 27: Phase 5 response keys remain intact in /matching
# ==============================================================================


def test_27_existing_phase_5_keys_intact():
    print("\n" + "=" * 70)
    print("TEST 27: EXISTING PHASE 5 RESPONSE KEYS REMAIN INTACT")
    print("=" * 70)

    mock_resume = {
        "_id": "res_1",
        "upload_id": "batch_active_123",
        "filename": "alice.pdf",
        "status": "completed",
        "resume_data": {"name": "Alice"},
    }
    mock_resume_emb = {
        "_id": "emb_1",
        "upload_id": "batch_active_123",
        "filename": "alice.pdf",
        "embeddings": [{"section": "skills", "embedding": [0.1] * 1024}],
    }

    with (
        patch("app.api.matching.jd_repository.get_active", new_callable=AsyncMock) as m_jd,
        patch("app.api.matching.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as m_jd_emb,
        patch("app.api.matching.batch_repository.get_active", new_callable=AsyncMock) as m_batch,
        patch("app.api.matching.resume_repository.get", new_callable=AsyncMock) as m_res,
        patch("app.api.matching.resume_embedding_repository.get", new_callable=AsyncMock) as m_res_emb,
        patch("app.api.matching.hybrid_matching_service.match_resume", new_callable=AsyncMock) as m_match,
    ):
        m_jd.return_value = MOCK_JD_DOC
        m_jd_emb.return_value = MOCK_JD_EMB
        m_batch.return_value = MOCK_ACTIVE_BATCH
        m_res.return_value = mock_resume
        m_res_emb.return_value = mock_resume_emb
        m_match.return_value = SAMPLE_MATCH_PAYLOAD

        response = client.post(
            "/matching/match-resume",
            json={"upload_id": "batch_active_123", "filename": "alice.pdf"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        # Phase 5 key presence validation
        assert "exact_matching" in data
        assert "semantic_retrieval" in data
        assert "experience_matching" in data
        assert data["exact_matching"]["matched_required_skills"] == 2

    print_status("Test 27: Existing Phase 5 matching response keys intact and unmodified", True)


# ==============================================================================
# TEST 28: Batch isolation preserved in Ranking API
# ==============================================================================


def test_28_batch_isolation_preserved():
    print("\n" + "=" * 70)
    print("TEST 28: BATCH ISOLATION PRESERVED IN RANKING API")
    print("=" * 70)

    # Inactive / superseded batch
    mock_superseded = {
        "_id": "batch_old",
        "batch_id": "batch_old",
        "status": "superseded",
        "is_active": False,
    }

    with (
        patch("app.api.ranking.jd_repository.get_active", new_callable=AsyncMock) as m_jd,
        patch("app.api.ranking.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as m_jd_emb,
        patch("app.api.ranking.batch_repository.get_active", new_callable=AsyncMock) as m_batch,
        patch("app.api.ranking.batch_repository.get", new_callable=AsyncMock) as m_get_b,
    ):
        m_jd.return_value = MOCK_JD_DOC
        m_jd_emb.return_value = MOCK_JD_EMB
        m_batch.return_value = MOCK_ACTIVE_BATCH
        m_get_b.return_value = mock_superseded

        # Candidate from inactive batch requested
        response = client.post(
            "/ranking/rank-resume",
            json={"upload_id": "batch_old", "filename": "alice.pdf"},
        )
        assert response.status_code == 400
        assert "not the active candidate batch" in response.json()["detail"]

        # Batch ranking with inactive batch requested
        batch_resp = client.post(
            "/ranking/rank-batch",
            json={"upload_id": "batch_old"},
        )
        assert batch_resp.status_code == 400
        assert "not the active candidate batch" in batch_resp.json()["detail"]

    print_status("Test 28: Ranking endpoints reject inactive batch requests (HTTP 400)", True)


# ==============================================================================
# TEST 29: Active-JD behavior preserved in Ranking API
# ==============================================================================


def test_29_active_jd_behavior_preserved():
    print("\n" + "=" * 70)
    print("TEST 29: ACTIVE-JD BEHAVIOR PRESERVED IN RANKING API")
    print("=" * 70)

    # 1. No active JD found -> HTTP 404
    with patch("app.api.ranking.jd_repository.get_active", new_callable=AsyncMock) as m_jd:
        m_jd.return_value = None
        resp_no_jd = client.post("/ranking/rank-resume", json={"upload_id": "b1", "filename": "f.pdf"})
        assert resp_no_jd.status_code == 404
        assert "No active job description found" in resp_no_jd.json()["detail"]

    # 2. Missing JD embeddings -> HTTP 404
    with (
        patch("app.api.ranking.jd_repository.get_active", new_callable=AsyncMock) as m_jd,
        patch("app.api.ranking.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as m_jd_emb,
    ):
        m_jd.return_value = MOCK_JD_DOC
        m_jd_emb.return_value = None

        resp_no_emb = client.post("/ranking/rank-resume", json={"upload_id": "b1", "filename": "f.pdf"})
        assert resp_no_emb.status_code == 404
        assert "Embeddings not found for active job description" in resp_no_emb.json()["detail"]

    print_status("Test 29: Ranking API enforces active JD and embeddings existence (HTTP 404)", True)


# ==============================================================================
# TEST 30: Full explainable breakdown via single-resume ranking API
# ==============================================================================


def test_30_explainable_breakdown_api():
    print("\n" + "=" * 70)
    print("TEST 30: FULL EXPLAINABLE BREAKDOWN VIA RANKING API")
    print("=" * 70)

    mock_resume = {
        "_id": "res_1",
        "upload_id": "batch_active_123",
        "filename": "alice.pdf",
        "status": "completed",
        "resume_data": {"name": "Alice"},
    }
    mock_resume_emb = {
        "_id": "emb_1",
        "upload_id": "batch_active_123",
        "filename": "alice.pdf",
        "embeddings": [{"section": "skills", "embedding": [0.1] * 1024}],
    }

    with (
        patch("app.api.ranking.jd_repository.get_active", new_callable=AsyncMock) as m_jd,
        patch("app.api.ranking.jd_repository.get", new_callable=AsyncMock) as m_jd_get,
        patch("app.api.ranking.jd_embedding_repository.get_by_jd_id", new_callable=AsyncMock) as m_jd_emb,
        patch("app.api.ranking.batch_repository.get_active", new_callable=AsyncMock) as m_batch,
        patch("app.api.ranking.resume_repository.get", new_callable=AsyncMock) as m_res,
        patch("app.api.ranking.resume_embedding_repository.get", new_callable=AsyncMock) as m_res_emb,
        patch("app.ranking.ranking_service.hybrid_matching_service.match_resume", new_callable=AsyncMock) as m_match,
    ):
        m_jd.return_value = MOCK_JD_DOC
        m_jd_get.return_value = MOCK_JD_DOC
        m_jd_emb.return_value = MOCK_JD_EMB
        m_batch.return_value = MOCK_ACTIVE_BATCH
        m_res.return_value = mock_resume
        m_res_emb.return_value = mock_resume_emb
        m_match.return_value = SAMPLE_MATCH_PAYLOAD

        response = client.post(
            "/ranking/rank-resume",
            json={"upload_id": "batch_active_123", "filename": "alice.pdf"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Validate explainable schema fields
        assert data["upload_id"] == "batch_active_123"
        assert data["filename"] == "alice.pdf"
        assert data["status"] == "complete"
        assert isinstance(data["final_score"], (int, float))
        assert data["final_score"] > 0.0

        # Check breakdown
        breakdown = data["breakdown"]
        for cat in ["required_skills", "responsibilities", "tools_and_technologies", "experience_relevance"]:
            assert cat in breakdown
            cat_data = breakdown[cat]
            assert "score" in cat_data
            assert "original_weight" in cat_data
            assert "normalized_weight" in cat_data
            assert "weighted_contribution" in cat_data
            assert "total_criteria_count" in cat_data
            assert "qualifying_criteria_count" in cat_data
            assert "evidence" in cat_data

        # Check separate experience diagnostics
        exp_diag = data["experience_diagnostic"]
        assert exp_diag["minimum_years"] == 2.0
        assert exp_diag["relevant_duration_years"] == 3.0
        assert exp_diag["minimum_duration_satisfied"] is True
        assert exp_diag["maximum_duration_exceeded"] is False

    print_status("Test 30: POST /ranking/rank-resume returns complete transparent scoring breakdown", True)


def main():
    print("=" * 80)
    print("TALENTAI — PHASE 6 RANKING API & INTEGRATION TEST SUITE")
    print("=" * 80)

    test_24_candidates_ranked_descending()
    test_25_incomplete_candidates_separated_not_zero()
    test_26_equal_scores_tie_handling()
    test_27_existing_phase_5_keys_intact()
    test_28_batch_isolation_preserved()
    test_29_active_jd_behavior_preserved()
    test_30_explainable_breakdown_api()

    print("\n" + "=" * 80)
    print("ALL INTEGRATION TESTS (Cases 24 through 30) PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
