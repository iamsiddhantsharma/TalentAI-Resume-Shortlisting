"""
TalentAI — Stage 5C Integration Test Suite
Evidence-Based Experience Ranking Integration Verification

Verifies all 13 core requirements:
1. Feature flag False preserves legacy ranking behavior.
2. Feature flag True activates evidence-based Component D.
3. The experience contribution is weighted exactly once.
4. The four ranking weights remain unchanged.
5. No double-counting of legacy and evidence-based experience occurs.
6. Unsupported JD domains contribute zero similarity.
7. Duplicate JD domains are counted only once.
8. Multiple relevant roles use per-domain maximum similarity.
9. Invalid ratios cannot inflate duration.
10. IRRELEVANT, AMBIGUOUS, and INSUFFICIENT_INFORMATION receive zero credit.
11. Missing dates preserve qualitative relevance but produce zero duration factor.
12. Unbounded JD targets preserve G1-C behavior.
13. Existing ranking components remain unaffected.
"""

import sys
import os
import math

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.ranking.ranking_config import BASE_WEIGHTS, USE_EVIDENCE_BASED_EXPERIENCE
from app.ranking.ranking_service import RankingEngine
from app.schemas.job_description_object import JobDescriptionObject, ExperienceRequirement


def make_standard_jd(
    skills=None,
    responsibilities=None,
    tools=None,
    preferred_domains=None,
    min_years=3.0,
    max_years=5.0,
):
    """Create a test JobDescriptionObject."""
    exp_reqs = []
    if preferred_domains is not None or min_years is not None or max_years is not None:
        exp_reqs.append(
            ExperienceRequirement(
                minimum_years=min_years,
                maximum_years=max_years,
                preferred_domains=preferred_domains or ["Fintech"],
            )
        )
    return JobDescriptionObject(
        required_skills=skills or ["Python", "FastAPI"],
        responsibilities=responsibilities or ["Develop backend APIs"],
        tools_and_technologies=tools or ["Docker"],
        experience_requirements=exp_reqs,
    )


def make_standard_match_result(
    exp_experiences=None,
    duration_factor=0.8,
    relevant_duration_years=4.0,
    diagnostic_status="duration_calculated",
    saturation_target_years=5.0,
    range_status="bounded",
    aggregated_similarity=0.75,
    min_years=3.0,
    max_years=5.0,
):
    """Create a structured match result dict for scoring."""
    if exp_experiences is None:
        exp_experiences = [
            {
                "experience_index": 0,
                "role": "Senior Backend Engineer",
                "company": "Tech Corp",
                "decision": "RELEVANT",
                "relevant": True,
                "matched_domains": ["Fintech"],
                "relevance_ratio": 1.0,
                "relevant_duration_years": 4.0,
                "semantic_similarity": 0.85,
                "calibrated_similarity": 0.75,
                "relevant_work_summary": "Architected low latency payment processing gateways.",
            }
        ]

    return {
        "upload_id": "test_upload_1",
        "filename": "candidate_1.pdf",
        "jd_id": "jd_123",
        "exact_matching": {
            "total_required_skills": 2,
            "matched_required_skills": 2,
            "unmatched_required_skills": 0,
            "matches": [
                {"required_skill": "Python", "matched": True},
                {"required_skill": "FastAPI", "matched": True},
            ],
        },
        "semantic_retrieval": {
            "top_k": 5,
            "responsibilities_retrieval": {
                "top_k": 5,
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Develop backend APIs",
                        "matches": [
                            {"similarity": 0.82, "resume_text": "Built scalable backend APIs using FastAPI."}
                        ],
                    }
                ],
            },
            "tools_and_technologies_retrieval": {
                "top_k": 5,
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Docker",
                        "matches": [
                            {"similarity": 0.90, "resume_text": "Containerized microservices using Docker."}
                        ],
                    }
                ],
            },
        },
        "experience_matching": {
            "status": "complete",
            "diagnostic_status": diagnostic_status,
            "diagnostic_message": f"Experience evaluation status: {diagnostic_status}",
            "relevant_experience_found": len(exp_experiences) > 0,
            "relevant_duration_years": relevant_duration_years,
            "duration_factor": duration_factor,
            "saturation_target_years": saturation_target_years,
            "range_status": range_status,
            "minimum_years": min_years,
            "maximum_years": max_years,
            "minimum_duration_satisfied": True,
            "maximum_duration_exceeded": False,
            "aggregated_similarity": aggregated_similarity,
            "experiences": exp_experiences,
        },
    }


# ==============================================================================
# TEST 1: Rollback flag False preserves legacy ranking behavior
# ==============================================================================
def test_requirement_1_feature_flag_false_preserves_legacy():
    print("--- Running Test 1: Rollback Flag False Preserves Legacy Ranking ---")
    assert USE_EVIDENCE_BASED_EXPERIENCE is True, "USE_EVIDENCE_BASED_EXPERIENCE must be True by production default"

    engine = RankingEngine(use_evidence_based_experience=False)
    jd = make_standard_jd()
    match_res = make_standard_match_result()

    scored = engine.score_candidate(match_res, jd)

    assert scored.status == "complete", f"Candidate scoring failed: {scored.errors}, {scored.warnings}"
    # Legacy Component D evaluates categorical score: RELEVANT = 1.0 (100.0%)
    exp_breakdown = scored.breakdown["experience_relevance"]
    assert exp_breakdown.score == 100.0, f"Expected legacy score 100.0, got {exp_breakdown.score}"
    assert exp_breakdown.notes is None or "evidence_based" not in str(exp_breakdown.notes)
    
    # Check weighted contribution: 0.35 * 100 = 35.0
    assert exp_breakdown.weighted_contribution == 35.0
    print("PASS: Test 1 - Rollback flag False preserves legacy behavior")


# ==============================================================================
# TEST 2: Feature flag True activates evidence-based Component D
# ==============================================================================
def test_requirement_2_feature_flag_true_activates_evidence_based():
    print("--- Running Test 2: Feature Flag True Activates Evidence-Based Component D ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    jd = make_standard_jd(preferred_domains=["Fintech"])
    # Calibrated sim = 0.75, D_global = 0.80 -> E = 100 * 0.75 * 0.80 = 60.0
    match_res = make_standard_match_result(duration_factor=0.8, aggregated_similarity=0.75)

    scored = engine.score_candidate(match_res, jd)

    assert scored.status == "complete", f"Candidate scoring failed: {scored.errors}, {scored.warnings}"
    exp_breakdown = scored.breakdown["experience_relevance"]
    expected_e = round(100.0 * 0.75 * 0.80, 2)  # 60.0
    assert exp_breakdown.score == expected_e, f"Expected evidence-based score {expected_e}, got {exp_breakdown.score}"
    assert "evidence_based" in exp_breakdown.notes
    assert "S_agg (0.7500)" in exp_breakdown.notes
    assert "D_global (0.8000)" in exp_breakdown.notes
    print("PASS: Test 2 - Feature flag True activates evidence-based Component D")


# ==============================================================================
# TEST 3: The experience contribution is weighted exactly once
# ==============================================================================
def test_requirement_3_experience_contribution_weighted_exactly_once():
    print("--- Running Test 3: Experience Contribution Weighted Exactly Once ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    jd = make_standard_jd(preferred_domains=["Fintech"])
    match_res = make_standard_match_result(duration_factor=0.8, aggregated_similarity=0.75)

    scored = engine.score_candidate(match_res, jd)

    exp_breakdown = scored.breakdown["experience_relevance"]
    expected_e = 60.0
    expected_weighted_contrib = round(0.35 * expected_e, 4)  # 21.0
    assert exp_breakdown.weighted_contribution == expected_weighted_contrib

    # Verify that the sum of all category weighted contributions equals final_score
    calculated_final = sum(b.weighted_contribution for b in scored.breakdown.values())
    assert round(calculated_final, 2) == scored.final_score
    print("PASS: Test 3 - Experience contribution is weighted exactly once (0.35 * E)")


# ==============================================================================
# TEST 4: The four ranking weights remain unchanged
# ==============================================================================
def test_requirement_4_ranking_weights_immutable():
    print("--- Running Test 4: Ranking Weights Remain Unchanged ---")
    engine = RankingEngine()
    expected_weights = {
        "required_skills": 0.25,
        "responsibilities": 0.30,
        "tools_and_technologies": 0.10,
        "experience_relevance": 0.35,
    }
    assert BASE_WEIGHTS == expected_weights
    assert engine.base_weights == expected_weights
    assert sum(engine.base_weights.values()) == 1.0
    print("PASS: Test 4 - All 4 ranking weights remain strictly 25%, 30%, 10%, 35%")


# ==============================================================================
# TEST 5: No double-counting of legacy and evidence-based experience occurs
# ==============================================================================
def test_requirement_5_no_double_counting():
    print("--- Running Test 5: No Double-Counting of Legacy and Evidence-Based Experience ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    jd = make_standard_jd(preferred_domains=["Fintech"])
    match_res = make_standard_match_result(duration_factor=0.8, aggregated_similarity=0.75)

    scored = engine.score_candidate(match_res, jd)

    # Legacy score would have been 100.0 (contribution 35.0)
    # Evidence score is 60.0 (contribution 21.0)
    # Final score must reflect 21.0, not 35.0 + 21.0 = 56.0!
    skills_contrib = scored.breakdown["required_skills"].weighted_contribution
    resp_contrib = scored.breakdown["responsibilities"].weighted_contribution
    tools_contrib = scored.breakdown["tools_and_technologies"].weighted_contribution
    exp_contrib = scored.breakdown["experience_relevance"].weighted_contribution

    expected_total = round(skills_contrib + resp_contrib + tools_contrib + exp_contrib, 2)
    assert scored.final_score == expected_total
    assert scored.final_score < (expected_total + 35.0)
    print("PASS: Test 5 - No double-counting of legacy and evidence-based experience")


# ==============================================================================
# TEST 6: Unsupported JD domains contribute zero similarity
# ==============================================================================
def test_requirement_6_unsupported_domains_contribute_zero():
    print("--- Running Test 6: Unsupported JD Domains Contribute Zero Similarity ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    # 2 unique domains in JD
    jd = make_standard_jd(preferred_domains=["Fintech", "Healthcare"])
    
    # Candidate only supports Fintech (sim = 0.80). Healthcare is unsupported.
    experiences = [
        {
            "experience_index": 0,
            "role": "Fintech Engineer",
            "company": "Bank Corp",
            "decision": "RELEVANT",
            "relevant": True,
            "matched_domains": ["Fintech"],
            "relevance_ratio": 1.0,
            "relevant_duration_years": 5.0,
            "calibrated_similarity": 0.80,
            "relevant_work_summary": "Built payment systems.",
        }
    ]
    match_res = make_standard_match_result(
        exp_experiences=experiences,
        duration_factor=1.0,
        aggregated_similarity=0.40,  # (0.80 + 0.0) / 2 = 0.40
    )

    scored = engine.score_candidate(match_res, jd)
    exp_breakdown = scored.breakdown["experience_relevance"]
    
    # S_agg = (0.80 + 0.0) / 2 = 0.40, D_global = 1.0 -> E = 40.0
    assert exp_breakdown.score == 40.0, f"Expected 40.0, got {exp_breakdown.score}"
    assert exp_breakdown.qualifying_criteria_count == 1
    assert exp_breakdown.total_criteria_count == 2

    # Verify per-domain evidence provenance
    evidence = exp_breakdown.evidence
    fintech_ev = next(e for e in evidence if e["criterion"] == "Fintech")
    health_ev = next(e for e in evidence if e["criterion"] == "Healthcare")

    assert fintech_ev["best_relevance_score"] == 0.80
    assert fintech_ev["qualifies"] is True
    assert health_ev["best_relevance_score"] == 0.0
    assert health_ev["qualifies"] is False
    assert "No candidate experience qualified" in health_ev["reason"]
    print("PASS: Test 6 - Unsupported domain contributes zero similarity (S_m = 0.0)")


# ==============================================================================
# TEST 7: Duplicate JD domains are counted only once
# ==============================================================================
def test_requirement_7_duplicate_domains_counted_once():
    print("--- Running Test 7: Duplicate JD Domains Counted Only Once ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    # JD with case-insensitive duplicate domains
    jd = make_standard_jd(preferred_domains=["Fintech", "fintech", "FINTECH", "Healthcare"])
    
    # Unique domains deduplicated: M = 2
    criteria = engine.extract_jd_experience_criteria(jd)
    assert len(criteria) == 2
    assert criteria == ["Fintech", "Healthcare"]

    experiences = [
        {
            "experience_index": 0,
            "role": "Fintech Engineer",
            "company": "Bank Corp",
            "decision": "RELEVANT",
            "relevant": True,
            "matched_domains": ["Fintech"],
            "calibrated_similarity": 0.80,
            "relevant_duration_years": 5.0,
        },
        {
            "experience_index": 1,
            "role": "Healthcare Developer",
            "company": "Health Corp",
            "decision": "RELEVANT",
            "relevant": True,
            "matched_domains": ["Healthcare"],
            "calibrated_similarity": 0.60,
            "relevant_duration_years": 5.0,
        },
    ]
    match_res = make_standard_match_result(
        exp_experiences=experiences,
        duration_factor=1.0,
        aggregated_similarity=0.70,  # (0.80 + 0.60) / 2 = 0.70
    )

    scored = engine.score_candidate(match_res, jd)
    exp_breakdown = scored.breakdown["experience_relevance"]
    # E = 100 * 0.70 * 1.0 = 70.0
    assert exp_breakdown.score == 70.0
    assert exp_breakdown.total_criteria_count == 2
    print("PASS: Test 7 - Duplicate JD domains deduplicated case-insensitively (M = 2)")


# ==============================================================================
# TEST 8: Multiple relevant roles use per-domain maximum similarity
# ==============================================================================
def test_requirement_8_multiple_roles_use_max_similarity():
    print("--- Running Test 8: Multiple Relevant Roles Use Per-Domain Maximum Similarity ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    jd = make_standard_jd(preferred_domains=["Fintech"])

    # Two roles both supporting Fintech with calibrated similarities 0.60 and 0.85
    experiences = [
        {
            "experience_index": 0,
            "role": "Junior Fintech Analyst",
            "company": "Finance One",
            "decision": "RELEVANT",
            "relevant": True,
            "matched_domains": ["Fintech"],
            "calibrated_similarity": 0.60,
            "relevant_duration_years": 2.0,
        },
        {
            "experience_index": 1,
            "role": "Lead Fintech Architect",
            "company": "Global Bank",
            "decision": "RELEVANT",
            "relevant": True,
            "matched_domains": ["Fintech"],
            "calibrated_similarity": 0.85,
            "relevant_duration_years": 3.0,
        },
    ]
    match_res = make_standard_match_result(
        exp_experiences=experiences,
        duration_factor=1.0,
        aggregated_similarity=0.85,
    )

    scored = engine.score_candidate(match_res, jd)
    exp_breakdown = scored.breakdown["experience_relevance"]
    # max(0.60, 0.85) = 0.85 -> E = 85.0
    assert exp_breakdown.score == 85.0
    ev = exp_breakdown.evidence[0]
    assert ev["best_relevance_score"] == 0.85
    assert ev["supporting_role"] == "Lead Fintech Architect"
    print("PASS: Test 8 - Multiple roles supporting domain select maximum similarity (0.85)")


# ==============================================================================
# TEST 9: Invalid ratios cannot inflate duration
# ==============================================================================
def test_requirement_9_invalid_ratios_cannot_inflate_duration():
    print("--- Running Test 9: Invalid Ratios Cannot Inflate Duration ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    jd = make_standard_jd(preferred_domains=["Fintech"])

    # Duration factor clamped to [0.0, 1.0] even if upstream supplied > 1.0 or malformed
    match_res_inflated = make_standard_match_result(
        duration_factor=999.0,  # Malicious / invalid inflated factor
        aggregated_similarity=0.75,
    )

    scored = engine.score_candidate(match_res_inflated, jd)
    exp_breakdown = scored.breakdown["experience_relevance"]
    # D_global must clamp to 1.0 -> E <= 100 * 0.75 * 1.0 = 75.0
    assert exp_breakdown.score == 75.0, f"Expected 75.0, got {exp_breakdown.score}"
    print("PASS: Test 9 - Invalid or inflated ratios/factors safely clamped to 1.0 max")


# ==============================================================================
# TEST 10: IRRELEVANT, AMBIGUOUS, INSUFFICIENT_INFORMATION receive zero credit
# ==============================================================================
def test_requirement_10_negative_decisions_receive_zero_credit():
    print("--- Running Test 10: IRRELEVANT, AMBIGUOUS, INSUFFICIENT_INFORMATION Zero Credit ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    jd = make_standard_jd(preferred_domains=["Fintech"])

    negative_decisions = ["IRRELEVANT", "AMBIGUOUS", "INSUFFICIENT_INFORMATION"]
    for dec in negative_decisions:
        experiences = [
            {
                "experience_index": 0,
                "role": "Role A",
                "company": "Corp A",
                "decision": dec,
                "relevant": False,
                "matched_domains": ["Fintech"],
                "calibrated_similarity": 0.95,  # High similarity must be ignored!
                "relevant_duration_years": 5.0,
            }
        ]
        match_res = make_standard_match_result(
            exp_experiences=experiences,
            duration_factor=1.0,
            aggregated_similarity=0.0,
        )

        scored = engine.score_candidate(match_res, jd)
        exp_breakdown = scored.breakdown["experience_relevance"]
        assert exp_breakdown.score == 0.0, f"Decision {dec} received non-zero score {exp_breakdown.score}"
        assert exp_breakdown.qualifying_criteria_count == 0
        assert exp_breakdown.evidence[0]["best_relevance_score"] == 0.0
        assert exp_breakdown.evidence[0]["qualifies"] is False

    print("PASS: Test 10 - IRRELEVANT, AMBIGUOUS, and INSUFFICIENT_INFORMATION receive 0.0 credit")


# ==============================================================================
# TEST 11: Missing dates preserve qualitative relevance but produce zero duration factor
# ==============================================================================
def test_requirement_11_missing_dates_zero_duration_factor():
    print("--- Running Test 11: Missing Dates Zero Duration Factor (D_global = 0.0) ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    jd = make_standard_jd(preferred_domains=["Fintech"])

    # Candidate has RELEVANT role with high similarity, but missing dates (D_global = 0.0)
    experiences = [
        {
            "experience_index": 0,
            "role": "Senior Fintech Lead",
            "company": "Bank Corp",
            "decision": "RELEVANT",
            "relevant": True,
            "matched_domains": ["Fintech"],
            "calibrated_similarity": 0.90,
            "relevant_duration_years": 0.0,
            "date_status": "missing_dates",
        }
    ]
    match_res = make_standard_match_result(
        exp_experiences=experiences,
        duration_factor=0.0,
        relevant_duration_years=0.0,
        diagnostic_status="missing_dates",
        aggregated_similarity=0.90,
    )

    scored = engine.score_candidate(match_res, jd)
    exp_breakdown = scored.breakdown["experience_relevance"]
    # E = 100 * 0.90 * 0.0 = 0.0
    assert exp_breakdown.score == 0.0
    # But qualitative relevance was recognized (qualifying_criteria_count = 1)
    assert exp_breakdown.qualifying_criteria_count == 1
    assert exp_breakdown.evidence[0]["best_relevance_score"] == 0.90
    assert exp_breakdown.evidence[0]["qualifies"] is True
    # Diagnostics transparently show missing_dates
    assert scored.experience_diagnostic.diagnostic_status == "missing_dates"
    assert scored.experience_diagnostic.duration_factor == 0.0
    print("PASS: Test 11 - Missing dates preserve qualitative relevance with D_global = 0.0 (E = 0.0)")


# ==============================================================================
# TEST 12: Unbounded JD targets preserve G1-C behavior
# ==============================================================================
def test_requirement_12_unbounded_jd_preserves_g1c():
    print("--- Running Test 12: Unbounded JD Preserves G1-C Behavior ---")
    engine = RankingEngine(use_evidence_based_experience=True)
    # JD with no min and no max years (unbounded)
    jd = make_standard_jd(preferred_domains=["Fintech"], min_years=None, max_years=None)

    match_res = make_standard_match_result(
        duration_factor=0.0,
        saturation_target_years=None,
        range_status="unspecified",
        min_years=None,
        max_years=None,
        aggregated_similarity=0.85,
    )

    scored = engine.score_candidate(match_res, jd)
    exp_breakdown = scored.breakdown["experience_relevance"]
    # In G1-C, D_global = 0.0 -> E = 0.0
    assert exp_breakdown.score == 0.0
    assert scored.experience_diagnostic.range_status == "unspecified"
    assert scored.experience_diagnostic.saturation_target_years is None
    assert scored.experience_diagnostic.duration_factor == 0.0
    print("PASS: Test 12 - Unbounded JD preserves G1-C behavior (range_status='unspecified', D=0.0)")


# ==============================================================================
# TEST 13: Existing ranking components remain unaffected
# ==============================================================================
def test_requirement_13_existing_components_unaffected():
    print("--- Running Test 13: Existing Components Unaffected by Flag State ---")
    engine_false = RankingEngine(use_evidence_based_experience=False)
    engine_true = RankingEngine(use_evidence_based_experience=True)

    jd = make_standard_jd(preferred_domains=["Fintech"])
    match_res = make_standard_match_result()

    scored_false = engine_false.score_candidate(match_res, jd)
    scored_true = engine_true.score_candidate(match_res, jd)

    # Component A: Skills
    assert scored_false.component_scores["required_skills"] == scored_true.component_scores["required_skills"]
    assert scored_false.breakdown["required_skills"].score == scored_true.breakdown["required_skills"].score
    assert scored_false.breakdown["required_skills"].evidence == scored_true.breakdown["required_skills"].evidence

    # Component B: Responsibilities
    assert scored_false.component_scores["responsibilities"] == scored_true.component_scores["responsibilities"]
    assert scored_false.breakdown["responsibilities"].score == scored_true.breakdown["responsibilities"].score
    assert scored_false.breakdown["responsibilities"].evidence == scored_true.breakdown["responsibilities"].evidence

    # Component C: Tools
    assert scored_false.component_scores["tools_and_technologies"] == scored_true.component_scores["tools_and_technologies"]
    assert scored_false.breakdown["tools_and_technologies"].score == scored_true.breakdown["tools_and_technologies"].score
    assert scored_false.breakdown["tools_and_technologies"].evidence == scored_true.breakdown["tools_and_technologies"].evidence

    # Weights
    for cat in ["required_skills", "responsibilities", "tools_and_technologies", "experience_relevance"]:
        assert scored_false.breakdown[cat].original_weight == scored_true.breakdown[cat].original_weight
        assert scored_false.breakdown[cat].normalized_weight == scored_true.breakdown[cat].normalized_weight

    print("PASS: Test 13 - Skills, responsibilities, and tools components completely unaffected")


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================
def run_all_tests():
    print("=" * 80)
    print("STARTING STAGE 5C RANKING INTEGRATION TEST SUITE (13 REQUIREMENTS)")
    print("=" * 80)

    test_requirement_1_feature_flag_false_preserves_legacy()
    test_requirement_2_feature_flag_true_activates_evidence_based()
    test_requirement_3_experience_contribution_weighted_exactly_once()
    test_requirement_4_ranking_weights_immutable()
    test_requirement_5_no_double_counting()
    test_requirement_6_unsupported_domains_contribute_zero()
    test_requirement_7_duplicate_domains_counted_once()
    test_requirement_8_multiple_roles_use_max_similarity()
    test_requirement_9_invalid_ratios_cannot_inflate_duration()
    test_requirement_10_negative_decisions_receive_zero_credit()
    test_requirement_11_missing_dates_zero_duration_factor()
    test_requirement_12_unbounded_jd_preserves_g1c()
    test_requirement_13_existing_components_unaffected()

    print("=" * 80)
    print("ALL 13 STAGE 5C RANKING INTEGRATION REQUIREMENTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
