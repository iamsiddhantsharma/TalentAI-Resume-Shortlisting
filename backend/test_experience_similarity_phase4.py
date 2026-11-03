"""
TalentAI — Phase 4 Unit Tests: Semantic Similarity & Calibration

Tests mathematical correctness, normalization/clamping, zero-credit safeguards,
missing summary handling, empty requirement handling, provenance/explainability,
and live BGE embedding behavior.
"""

import math
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.experience_similarity_service import (
    ExperienceSimilarityService,
    experience_similarity_service,
)


# =============================================================================
# TEST GROUP 1: PURE MATHEMATICAL FUNCTIONS
# =============================================================================

def test_cosine_similarity_identical_vectors():
    svc = experience_similarity_service
    vec = [1.0, 2.0, 3.0, 4.0]
    sim = svc.cosine_similarity(vec, vec)
    assert abs(sim - 1.0) < 1e-6, f"Expected 1.0, got {sim}"
    print("PASS: test_cosine_similarity_identical_vectors")


def test_cosine_similarity_orthogonal_vectors():
    svc = experience_similarity_service
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.0, 1.0, 0.0]
    sim = svc.cosine_similarity(vec_a, vec_b)
    assert abs(sim - 0.0) < 1e-6, f"Expected 0.0, got {sim}"
    print("PASS: test_cosine_similarity_orthogonal_vectors")


def test_cosine_similarity_opposite_vectors():
    svc = experience_similarity_service
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [-1.0, -2.0, -3.0]
    sim = svc.cosine_similarity(vec_a, vec_b)
    assert abs(sim - (-1.0)) < 1e-6, f"Expected -1.0, got {sim}"
    print("PASS: test_cosine_similarity_opposite_vectors")


def test_cosine_similarity_dimension_mismatch():
    svc = experience_similarity_service
    try:
        svc.cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
        assert False, "Expected ValueError on dimension mismatch"
    except ValueError as e:
        assert "dimension mismatch" in str(e).lower()
    print("PASS: test_cosine_similarity_dimension_mismatch")


def test_cosine_similarity_empty_vectors():
    svc = experience_similarity_service
    try:
        svc.cosine_similarity([], [])
        assert False, "Expected ValueError on empty vectors"
    except ValueError as e:
        assert "cannot be empty" in str(e).lower()
    print("PASS: test_cosine_similarity_empty_vectors")


def test_cosine_similarity_zero_vector():
    svc = experience_similarity_service
    try:
        svc.cosine_similarity([0.0, 0.0], [1.0, 2.0])
        assert False, "Expected ValueError on zero vector"
    except ValueError as e:
        assert "zero vector" in str(e).lower()
    print("PASS: test_cosine_similarity_zero_vector")


# =============================================================================
# TEST GROUP 2: CALIBRATION FORMULA & CLAMPING
# =============================================================================

def test_calibration_below_threshold():
    svc = experience_similarity_service
    # raw_similarity < tau should return strictly 0.0
    cal = svc.calibrate_similarity(0.60, tau=0.65)
    assert cal == 0.0, f"Expected 0.0, got {cal}"

    cal2 = svc.calibrate_similarity(0.40, tau=0.65)
    assert cal2 == 0.0, f"Expected 0.0, got {cal2}"
    print("PASS: test_calibration_below_threshold")


def test_calibration_at_threshold():
    svc = experience_similarity_service
    # raw_similarity == tau should return 0.0
    cal = svc.calibrate_similarity(0.65, tau=0.65)
    assert cal == 0.0, f"Expected 0.0, got {cal}"
    print("PASS: test_calibration_at_threshold")


def test_calibration_at_saturation():
    svc = experience_similarity_service
    # raw_similarity == 1.0 should return 1.0
    cal = svc.calibrate_similarity(1.0, tau=0.65)
    assert abs(cal - 1.0) < 1e-6, f"Expected 1.0, got {cal}"
    print("PASS: test_calibration_at_saturation")


def test_calibration_midpoint():
    svc = experience_similarity_service
    # For tau=0.65: midpoint is 0.65 + 0.5 * (1.0 - 0.65) = 0.825
    cal = svc.calibrate_similarity(0.825, tau=0.65)
    assert abs(cal - 0.5) < 1e-6, f"Expected 0.5, got {cal}"
    print("PASS: test_calibration_midpoint")


def test_calibration_clamping_upper_bound():
    svc = experience_similarity_service
    # Any value > 1.0 due to floating point quirks must clamp to 1.0
    cal = svc.calibrate_similarity(1.05, tau=0.65)
    assert cal == 1.0, f"Expected 1.0, got {cal}"
    print("PASS: test_calibration_clamping_upper_bound")


def test_calibration_boundary_tau_1():
    svc = experience_similarity_service
    assert svc.calibrate_similarity(0.99, tau=1.0) == 0.0
    assert svc.calibrate_similarity(1.0, tau=1.0) == 1.0
    print("PASS: test_calibration_boundary_tau_1")


# =============================================================================
# TEST GROUP 3: ZERO-CREDIT SAFEGUARDS
# =============================================================================

def test_zero_credit_irrelevant_role():
    svc = experience_similarity_service
    res = svc.evaluate_experience_similarity(
        decision="IRRELEVANT",
        relevant_work_summary="Trained high-accuracy convolutional neural networks in PyTorch.",
        jd_requirements=["Machine Learning and Deep Learning"],
    )
    assert res["eligible"] is False
    assert res["raw_similarity"] == 0.0
    assert res["calibrated_similarity"] == 0.0
    assert res["diagnostic_status"] == "zero_credit_non_relevant"
    assert "IRRELEVANT" in res["diagnostic_message"]
    print("PASS: test_zero_credit_irrelevant_role")


def test_zero_credit_ambiguous_role():
    svc = experience_similarity_service
    res = svc.evaluate_experience_similarity(
        decision="AMBIGUOUS",
        relevant_work_summary="Worked with algorithms and data.",
        jd_requirements=["Machine Learning"],
    )
    assert res["eligible"] is False
    assert res["raw_similarity"] == 0.0
    assert res["calibrated_similarity"] == 0.0
    assert res["diagnostic_status"] == "zero_credit_non_relevant"
    print("PASS: test_zero_credit_ambiguous_role")


def test_zero_credit_insufficient_information():
    svc = experience_similarity_service
    res = svc.evaluate_experience_similarity(
        decision="INSUFFICIENT_INFORMATION",
        relevant_work_summary="Attended machine learning meeting.",
        jd_requirements=["Machine Learning"],
    )
    assert res["eligible"] is False
    assert res["raw_similarity"] == 0.0
    assert res["calibrated_similarity"] == 0.0
    assert res["diagnostic_status"] == "zero_credit_non_relevant"
    print("PASS: test_zero_credit_insufficient_information")


def test_zero_credit_none_decision():
    svc = experience_similarity_service
    res = svc.evaluate_experience_similarity(
        decision=None,
        relevant_work_summary="Some work",
        jd_requirements=["Machine Learning"],
    )
    assert res["eligible"] is False
    assert res["raw_similarity"] == 0.0
    assert res["calibrated_similarity"] == 0.0
    assert res["diagnostic_status"] == "zero_credit_non_relevant"
    print("PASS: test_zero_credit_none_decision")


def test_zero_credit_missing_summary_on_relevant_role():
    svc = experience_similarity_service
    # Relevant role, but summary is None
    res = svc.evaluate_experience_similarity(
        decision="RELEVANT",
        relevant_work_summary=None,
        jd_requirements=["Machine Learning"],
    )
    assert res["eligible"] is False
    assert res["raw_similarity"] == 0.0
    assert res["calibrated_similarity"] == 0.0
    assert res["diagnostic_status"] == "missing_work_summary"

    # Whitespace only summary
    res_empty = svc.evaluate_experience_similarity(
        decision="RELEVANT",
        relevant_work_summary="    ",
        jd_requirements=["Machine Learning"],
    )
    assert res_empty["eligible"] is False
    assert res_empty["diagnostic_status"] == "missing_work_summary"
    print("PASS: test_zero_credit_missing_summary_on_relevant_role")


def test_zero_credit_missing_jd_requirements():
    svc = experience_similarity_service
    res = svc.evaluate_experience_similarity(
        decision="RELEVANT",
        relevant_work_summary="Trained PyTorch models.",
        jd_requirements=[],
    )
    assert res["eligible"] is False
    assert res["raw_similarity"] == 0.0
    assert res["calibrated_similarity"] == 0.0
    assert res["diagnostic_status"] == "missing_jd_requirements"
    print("PASS: test_zero_credit_missing_jd_requirements")


# =============================================================================
# TEST GROUP 4: DETERMINISTIC EVALUATION WITH PRECOMPUTED VECTORS
# =============================================================================

def test_deterministic_multi_domain_matching():
    svc = experience_similarity_service
    # 3-dim synthetic unit vectors
    cand_emb = [0.8, 0.6, 0.0]
    domain_embs = {
        "Computer Vision": [0.8, 0.6, 0.0],  # sim = 1.0 -> calibrated = 1.0
        "Natural Language Processing": [0.0, 1.0, 0.0],  # sim = 0.6 -> calibrated = 0.0
        "Databases": [0.0, 0.0, 1.0],  # sim = 0.0 -> calibrated = 0.0
    }

    res = svc.evaluate_experience_similarity(
        decision="RELEVANT",
        relevant_work_summary="Implemented convolutional neural network for image classification.",
        jd_requirements=list(domain_embs.keys()),
        tau=0.65,
        candidate_embedding=cand_emb,
        jd_embeddings=domain_embs,
    )

    assert res["eligible"] is True
    assert res["best_matching_requirement"] == "Computer Vision"
    assert abs(res["raw_similarity"] - 1.0) < 1e-4
    assert abs(res["calibrated_similarity"] - 1.0) < 1e-4
    assert len(res["all_domain_similarities"]) == 3
    assert res["diagnostic_status"] == "similarity_calculated"
    print("PASS: test_deterministic_multi_domain_matching")


def test_deterministic_partially_relevant_role():
    svc = experience_similarity_service
    # Candidate vector with similarity 0.79 to domain requirement
    # calibrated = (0.79 - 0.65) / 0.35 = 0.14 / 0.35 = 0.40
    cand_emb = [0.79, 0.6131, 0.0]
    domain_emb = [1.0, 0.0, 0.0]

    res = svc.evaluate_experience_similarity(
        decision="PARTIALLY_RELEVANT",
        relevant_work_summary="Trained Random Forest model part time.",
        jd_requirements=["Predictive Modeling"],
        tau=0.65,
        candidate_embedding=cand_emb,
        jd_embeddings=[domain_emb],
    )

    assert res["eligible"] is True
    assert res["decision"] == "PARTIALLY_RELEVANT"
    assert abs(res["raw_similarity"] - 0.79) < 1e-3
    assert abs(res["calibrated_similarity"] - 0.40) < 1e-3
    print("PASS: test_deterministic_partially_relevant_role")


# =============================================================================
# TEST GROUP 5: PROVENANCE & EXPLAINABILITY
# =============================================================================

def test_provenance_and_explainability_fields():
    svc = experience_similarity_service
    res = svc.evaluate_experience_similarity(
        decision="RELEVANT",
        relevant_work_summary="Developed deep learning NLP models.",
        jd_requirements=["Natural Language Processing"],
        tau=0.65,
        candidate_embedding=[1.0, 0.0],
        jd_embeddings=[[1.0, 0.0]],
    )

    expected_keys = {
        "eligible",
        "decision",
        "raw_similarity",
        "calibrated_similarity",
        "tau",
        "model_name",
        "relevant_work_summary",
        "best_matching_requirement",
        "all_domain_similarities",
        "diagnostic_status",
        "diagnostic_message",
    }
    assert expected_keys.issubset(res.keys()), f"Missing keys: {expected_keys - set(res.keys())}"
    assert res["model_name"] == "BAAI/bge-large-en-v1.5"
    assert res["tau"] == 0.65
    assert "developed deep learning nlp models" in res["relevant_work_summary"].lower()
    print("PASS: test_provenance_and_explainability_fields")


# =============================================================================
# TEST GROUP 6: LIVE EMBEDDING INTEGRATION (SentenceTransformer BGE)
# =============================================================================

def test_live_bge_genuine_ml_vs_transferable_backend():
    svc = experience_similarity_service

    jd_req = "Machine Learning, Deep Learning, and Artificial Intelligence"

    # Case A: Genuine ML
    ml_summary = (
        "Designed and trained PyTorch convolutional neural networks for semantic image segmentation; "
        "optimized cross-entropy loss, achieving 0.88 mIoU on test benchmarks."
    )
    ml_res = svc.evaluate_experience_similarity(
        decision="RELEVANT",
        relevant_work_summary=ml_summary,
        jd_requirements=[jd_req],
        tau=0.65,
    )
    assert ml_res["eligible"] is True
    assert ml_res["raw_similarity"] > 0.65, f"Expected raw > 0.65, got {ml_res['raw_similarity']}"
    assert ml_res["calibrated_similarity"] > 0.0, f"Expected calibrated > 0, got {ml_res['calibrated_similarity']}"

    # Case B: Transferable Backend (Diwakar case)
    # Even if an erroneous decision was passed, raw similarity alone against ML JD is < 0.65!
    backend_summary = (
        "Built REST APIs using Flask and Python, integrated Azure Cosmos DB, "
        "and configured Swagger documentation."
    )
    backend_res = svc.evaluate_experience_similarity(
        decision="RELEVANT",
        relevant_work_summary=backend_summary,
        jd_requirements=[jd_req],
        tau=0.65,
    )
    # Raw similarity should be below 0.65
    assert backend_res["raw_similarity"] < 0.65, (
        f"Backend summary raw similarity ({backend_res['raw_similarity']}) was unexpectedly >= 0.65"
    )
    # Calibrated similarity must be 0.0!
    assert backend_res["calibrated_similarity"] == 0.0, (
        f"Backend summary calibrated similarity ({backend_res['calibrated_similarity']}) must be 0.0"
    )

    # Case C: Transferable Backend with proper Phase 2 IRRELEVANT decision
    backend_irrelevant = svc.evaluate_experience_similarity(
        decision="IRRELEVANT",
        relevant_work_summary=backend_summary,
        jd_requirements=[jd_req],
        tau=0.65,
    )
    assert backend_irrelevant["eligible"] is False
    assert backend_irrelevant["raw_similarity"] == 0.0
    assert backend_irrelevant["calibrated_similarity"] == 0.0
    assert backend_irrelevant["diagnostic_status"] == "zero_credit_non_relevant"

    print("PASS: test_live_bge_genuine_ml_vs_transferable_backend")


if __name__ == "__main__":
    print("\n--- Running Phase 4 Experience Similarity Unit Tests ---")
    test_cosine_similarity_identical_vectors()
    test_cosine_similarity_orthogonal_vectors()
    test_cosine_similarity_opposite_vectors()
    test_cosine_similarity_dimension_mismatch()
    test_cosine_similarity_empty_vectors()
    test_cosine_similarity_zero_vector()

    test_calibration_below_threshold()
    test_calibration_at_threshold()
    test_calibration_at_saturation()
    test_calibration_midpoint()
    test_calibration_clamping_upper_bound()
    test_calibration_boundary_tau_1()

    test_zero_credit_irrelevant_role()
    test_zero_credit_ambiguous_role()
    test_zero_credit_insufficient_information()
    test_zero_credit_none_decision()
    test_zero_credit_missing_summary_on_relevant_role()
    test_zero_credit_missing_jd_requirements()

    test_deterministic_multi_domain_matching()
    test_deterministic_partially_relevant_role()
    test_provenance_and_explainability_fields()

    print("\n--- Running Live BGE Embedding Test ---")
    test_live_bge_genuine_ml_vs_transferable_backend()

    print("\n=== ALL 16 PHASE 4 UNIT TESTS PASSED ===")
