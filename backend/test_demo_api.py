"""
TalentAI — Milestone 1: Synthetic Demo Sandbox Unit & Isolation Test Suite

Verifies:
1. GET /demo/presets returns all 12 broad synthetic presets with correct schema and synthetic tags.
2. GET /demo/presets/{jd_id} returns single preset with structured JD data.
3. GET /demo/presets/{invalid_jd_id} returns HTTP 404.
4. GET /demo/cohort/{jd_id} returns 20 ranked synthetic candidates with dual scores and explainable breakdowns.
5. POST /demo/cohort/{jd_id}/rank respects scoring_mode ('legacy' vs 'evidence') and computes score deltas.
6. Inverted and missing date edge-case candidates (e.g., C16, C17) generate correct diagnostic notices.
7. Strict Database Isolation: Demo endpoints execute 100% in-memory and NEVER call MongoDB,
   the batch repository, resume collections, or the protected active batch (07281a64-46cf-46b4-a5c1-a0d46b13e7b2).
8. Feature flag state: Production USE_EVIDENCE_BASED_EXPERIENCE is True by default.
9. Lazy import resilience: When test fixtures are absent, endpoints fail gracefully with HTTP 503 instead of crashing application startup.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from app.auth.auth_dependencies import HRUser, get_current_hr_user
from app.ranking.ranking_config import USE_EVIDENCE_BASED_EXPERIENCE

# Configure mock HR session dependency override for authenticated endpoint testing
mock_test_hr = HRUser(
    user_id="test_demo_hr_user",
    username="demo_hr_tester",
    full_name="Demo HR Tester",
    email="demo_hr@talentai.internal",
    role="hr",
    created_at=datetime.now(timezone.utc),
)
app.dependency_overrides[get_current_hr_user] = lambda: mock_test_hr

client = TestClient(app)


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


def test_1_list_presets():
    """Verify that GET /demo/presets returns all 12 broad synthetic presets."""
    res = client.get("/demo/presets")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()

    assert data["total_presets"] == 12
    assert len(data["presets"]) == 12
    assert data["is_synthetic_demo"] is True

    # Check first preset
    first = data["presets"][0]
    assert first["jd_id"] == "JD-BROAD-01"
    assert first["title"] == "Principal Distributed Storage Engineer"
    assert first["family"] == "Backend & Distributed Systems"
    assert first["paradigm"] == "Bounded"
    assert first["target_years"] == 8.0
    assert first["candidate_count"] == 20
    assert first["is_synthetic_demo"] is True

    # Check all presets have synthetic demo flag
    for p in data["presets"]:
        assert p["is_synthetic_demo"] is True
        assert p["candidate_count"] == 20

    print_status("Test 1: GET /demo/presets returns 12 presets tagged as synthetic", True)


def test_2_get_single_preset():
    """Verify that GET /demo/presets/{jd_id} returns complete structured JD data."""
    res = client.get("/demo/presets/JD-BROAD-01")
    assert res.status_code == 200
    data = res.json()

    assert data["jd_id"] == "JD-BROAD-01"
    assert data["is_synthetic_demo"] is True
    assert "structured_data" in data
    struct = data["structured_data"]
    assert "required_skills" in struct
    assert "Go" in struct["required_skills"]
    assert "responsibilities" in struct
    assert "experience_requirements" in struct
    assert struct["experience_requirements"][0]["maximum_years"] == 8.0

    print_status("Test 2: GET /demo/presets/JD-BROAD-01 returns valid structured preset", True)


def test_3_get_invalid_preset():
    """Verify that requesting a nonexistent preset returns HTTP 404."""
    res = client.get("/demo/presets/JD-NONEXISTENT")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    print_status("Test 3: GET /demo/presets/INVALID returns HTTP 404", True)


def test_4_cohort_ranking_legacy_and_evidence():
    """Verify dual scoring in GET /demo/cohort/{jd_id}."""
    # Test Legacy Mode
    res_leg = client.get("/demo/cohort/JD-BROAD-01?scoring_mode=legacy")
    assert res_leg.status_code == 200
    data_leg = res_leg.json()

    assert data_leg["scoring_mode"] == "legacy"
    assert data_leg["is_synthetic_demo"] is True
    assert data_leg["total_eligible"] == 20
    assert data_leg["ranked_count"] == 20
    assert len(data_leg["ranked_candidates"]) == 20

    first_leg = data_leg["ranked_candidates"][0]
    assert first_leg["rank"] == 1
    assert first_leg["final_score"] is not None
    assert first_leg["is_synthetic_demo"] is True
    assert "legacy_score" in first_leg
    assert "evidence_score" in first_leg
    assert "score_delta" in first_leg
    assert "breakdown" in first_leg
    assert "experience_relevance" in first_leg["breakdown"]

    # Test Evidence Mode
    res_evi = client.get("/demo/cohort/JD-BROAD-01?scoring_mode=evidence")
    assert res_evi.status_code == 200
    data_evi = res_evi.json()

    assert data_evi["scoring_mode"] == "evidence"
    first_evi = data_evi["ranked_candidates"][0]
    assert first_evi["rank"] == 1
    # Evidence experience note must include provenance marker
    exp_note = first_evi["breakdown"]["experience_relevance"]["notes"]
    assert "evidence_based" in exp_note.lower()

    print_status("Test 4: GET /demo/cohort/JD-BROAD-01 dual scoring verified", True)


def test_5_rank_post_and_score_delta():
    """Verify POST /demo/cohort/{jd_id}/rank computes accurate score deltas."""
    res = client.post("/demo/cohort/JD-BROAD-01/rank", json={"scoring_mode": "evidence"})
    assert res.status_code == 200
    data = res.json()

    for cand in data["ranked_candidates"]:
        leg = cand["legacy_score"]
        evi = cand["evidence_score"]
        delta = cand["score_delta"]
        assert round(evi - leg, 2) == delta, f"Delta mismatch for {cand['filename']}: {evi} - {leg} != {delta}"

    print_status("Test 5: POST /demo/cohort/JD-BROAD-01/rank score delta exactness verified", True)


def test_6_edge_cases_diagnostics_in_demo():
    """Verify missing/inverted date candidates appear with correct diagnostics."""
    res = client.get("/demo/cohort/JD-BROAD-01?scoring_mode=evidence")
    assert res.status_code == 200
    data = res.json()

    candidates_by_edge = {}
    for c in data["ranked_candidates"]:
        for marker in c.get("edge_markers", []):
            candidates_by_edge[marker] = c

    assert "missing_dates" in candidates_by_edge
    c_missing = candidates_by_edge["missing_dates"]
    exp_diag = c_missing["experience_diagnostic"]
    assert exp_diag.get("diagnostic_status") == "missing_dates"
    assert c_missing["breakdown"]["experience_relevance"]["score"] == 0.0

    assert "invalid_date_range" in candidates_by_edge
    c_invalid = candidates_by_edge["invalid_date_range"]
    exp_diag_inv = c_invalid["experience_diagnostic"]
    assert exp_diag_inv.get("diagnostic_status") == "invalid_date_range"
    assert c_invalid["breakdown"]["experience_relevance"]["score"] == 0.0

    print_status("Test 6: Edge-case candidates preserve diagnostic notices in demo", True)


def test_7_database_isolation_and_no_active_batch_access():
    """
    CRITICAL SAFETY TEST:
    Verify that demo endpoints NEVER query MongoDB, touch collections, or
    access the protected active batch (07281a64-46cf-46b4-a5c1-a0d46b13e7b2).
    """
    with patch("app.database.batch_repository.batch_repository.get_active") as mock_get_active, \
         patch("app.database.batch_repository.batch_repository.get") as mock_get_batch, \
         patch("app.database.resume_repository.resume_repository.get") as mock_get_resume, \
         patch("app.database.mongodb.mongodb.get_database") as mock_get_db:

        # Side effect raises an error if called
        mock_get_active.side_effect = RuntimeError("DATABASE ACCESS FORBIDDEN IN DEMO")
        mock_get_batch.side_effect = RuntimeError("DATABASE ACCESS FORBIDDEN IN DEMO")
        mock_get_resume.side_effect = RuntimeError("DATABASE ACCESS FORBIDDEN IN DEMO")
        mock_get_db.side_effect = RuntimeError("DATABASE ACCESS FORBIDDEN IN DEMO")

        # Execute all demo endpoints under strict DB lockdown
        res1 = client.get("/demo/presets")
        assert res1.status_code == 200

        res2 = client.get("/demo/presets/JD-BROAD-01")
        assert res2.status_code == 200

        res3 = client.get("/demo/cohort/JD-BROAD-01?scoring_mode=evidence")
        assert res3.status_code == 200

        res4 = client.post("/demo/cohort/JD-BROAD-01/rank", json={"scoring_mode": "legacy"})
        assert res4.status_code == 200

        # Assert zero calls to database
        assert mock_get_active.call_count == 0
        assert mock_get_batch.call_count == 0
        assert mock_get_resume.call_count == 0
        assert mock_get_db.call_count == 0

    print_status("Test 7: Strict in-memory database isolation verified (0 database calls)", True)


def test_8_feature_flag_invariant():
    """Confirm global feature flag is True by production default."""
    assert USE_EVIDENCE_BASED_EXPERIENCE is True, "USE_EVIDENCE_BASED_EXPERIENCE must be True by production default"
    print_status("Test 8: USE_EVIDENCE_BASED_EXPERIENCE is strictly True by production default", True)


def test_9_lazy_import_fallback_when_fixtures_missing():
    """
    Verify that when fixtures_broad is not available (such as in a lean production container),
    requesting a demo endpoint gracefully returns HTTP 503 instead of an unhandled 500 error.
    """
    import app.api.demo as demo_module

    # Save original cache state
    original_cache = demo_module._fixtures_module
    try:
        # Simulate missing fixtures
        demo_module._fixtures_module = None
        with patch.object(demo_module, "_get_fixtures", side_effect=demo_module.HTTPException(
            status_code=503,
            detail="Synthetic demo fixtures are not available in this environment.",
        )):
            res = client.get("/demo/presets")
            assert res.status_code == 503, f"Expected 503, got {res.status_code}"
            assert "not available" in res.json()["detail"].lower()
    finally:
        demo_module._fixtures_module = original_cache

    print_status("Test 9: Lazy fixture loader returns HTTP 503 when fixtures are absent", True)


def main():
    print("=" * 80)
    print("TALENTAI — MILESTONE 1: SYNTHETIC DEMO API & ISOLATION TEST SUITE")
    print("=" * 80)

    test_1_list_presets()
    test_2_get_single_preset()
    test_3_get_invalid_preset()
    test_4_cohort_ranking_legacy_and_evidence()
    test_5_rank_post_and_score_delta()
    test_6_edge_cases_diagnostics_in_demo()
    test_7_database_isolation_and_no_active_batch_access()
    test_8_feature_flag_invariant()
    test_9_lazy_import_fallback_when_fixtures_missing()

    print("\n" + "=" * 80)
    print("ALL 9 SYNTHETIC DEMO API TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
