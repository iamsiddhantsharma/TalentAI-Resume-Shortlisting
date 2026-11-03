"""
TalentAI — Phase 6: Ranking Engine Unit Test Suite

Tests:
A. Base Formula (Cases 1-3)
B. Weight Renormalization (Cases 4-8)
C. Missing Evidence and Service Failures (Cases 9-14)
D. Experience Relevance Scoring & Denominator Invariance (Cases 15-23)
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ranking.ranking_config import BASE_WEIGHTS, SEMANTIC_RETRIEVAL_THRESHOLD
from app.ranking.ranking_schemas import (
    CandidateRankingResult,
    CategoryScoreBreakdown,
)
from app.ranking.ranking_service import RankingEngine, ranking_engine
from app.schemas.job_description_object import ExperienceRequirement, JobDescriptionObject
from app.schemas.matching import (
    CandidateExperienceItem,
    ExactMatchingResult,
    ExactSkillMatchItem,
    ExperienceMatchingResult,
    ExperienceRequirementSummary,
    ResumeMatchResult,
    SemanticEvidenceMatchItem,
    SemanticRetrievalRequirementResult,
    SemanticRetrievalResult,
    SemanticSectionRetrieval,
)


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


def run_unit_tests():
    print("=" * 80)
    print("TALENTAI — PHASE 6: RANKING ENGINE UNIT TEST SUITE")
    print("=" * 80)

    engine = ranking_engine

    # ==========================================================================
    # GROUP A: BASE FORMULA TESTS
    # ==========================================================================
    print("\n--- GROUP A: BASE FORMULA ---")

    # Case 1: Four applicable categories, all scores 100 -> final score 100
    jd_full = JobDescriptionObject(
        required_skills=["Python", "FastAPI"],
        responsibilities=["Develop microservices"],
        tools_and_technologies=["Docker"],
        experience_requirements=[ExperienceRequirement(preferred_domains=["Fintech"])],
    )
    raw_match_100 = {
        "upload_id": "b1",
        "filename": "cand1.pdf",
        "jd_id": "jd1",
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
                        "jd_text": "Develop microservices",
                        "matches": [{"similarity": 1.0, "resume_text": "Built services"}],
                    }
                ],
            },
            "tools_and_technologies_retrieval": {
                "top_k": 5,
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Docker",
                        "matches": [{"similarity": 1.0, "resume_text": "Docker containers"}],
                    }
                ],
            },
        },
        "experience_matching": {
            "experiences": [
                {"role": "Backend Dev", "relevant": True, "relevance_score": 1.0}
            ]
        },
    }
    res_1 = engine.score_candidate(raw_match_100, jd_full)
    assert res_1.status == "complete", f"Expected complete, got {res_1.status}"
    assert res_1.final_score == 100.0, f"Expected 100.0, got {res_1.final_score}"
    assert res_1.component_scores["required_skills"] == 100.0
    assert res_1.component_scores["responsibilities"] == 100.0
    assert res_1.component_scores["tools_and_technologies"] == 100.0
    assert res_1.component_scores["experience_relevance"] == 100.0
    print_status("Test 1: Four applicable categories, all scores 100 -> final score 100", True)

    # Case 2: Four applicable categories, all scores 0 -> final score 0
    raw_match_0 = {
        "upload_id": "b1",
        "filename": "cand2.pdf",
        "jd_id": "jd1",
        "exact_matching": {
            "total_required_skills": 2,
            "matched_required_skills": 0,
            "unmatched_required_skills": 2,
            "matches": [
                {"required_skill": "Python", "matched": False},
                {"required_skill": "FastAPI", "matched": False},
            ],
        },
        "semantic_retrieval": {
            "top_k": 5,
            "responsibilities_retrieval": {
                "top_k": 5,
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Develop microservices",
                        "matches": [{"similarity": 0.50}],  # below 0.65 threshold
                    }
                ],
            },
            "tools_and_technologies_retrieval": {
                "top_k": 5,
                "results": [
                    {
                        "jd_item_index": 0,
                        "jd_text": "Docker",
                        "matches": [],
                    }
                ],
            },
        },
        "experience_matching": {
            "experiences": [
                {"role": "Graphic Designer", "relevant": False, "decision": "IRRELEVANT"}
            ]
        },
    }
    res_2 = engine.score_candidate(raw_match_0, jd_full)
    assert res_2.status == "complete"
    assert res_2.final_score == 0.0, f"Expected 0.0, got {res_2.final_score}"
    assert res_2.component_scores["required_skills"] == 0.0
    assert res_2.component_scores["responsibilities"] == 0.0
    assert res_2.component_scores["tools_and_technologies"] == 0.0
    assert res_2.component_scores["experience_relevance"] == 0.0
    print_status("Test 2: Four applicable categories, all scores 0 -> final score 0", True)

    # Case 3: Scores of 80, 60, 40, and 90 with base weights 25%, 30%, 10%, 35% -> final score 73.5
    # Verification: 0.25*80 + 0.30*60 + 0.10*40 + 0.35*90 = 20 + 18 + 4 + 31.5 = 73.5
    raw_category_params = {
        "required_skills": 80.0,
        "responsibilities": 60.0,
        "tools_and_technologies": 40.0,
        "experience_relevance": 90.0,
    }
    norm_w = engine.normalize_weights(
        {
            "required_skills": "applicable",
            "responsibilities": "applicable",
            "tools_and_technologies": "applicable",
            "experience_relevance": "applicable",
        }
    )
    final_score_3 = sum(norm_w[c] * raw_category_params[c] for c in norm_w)
    assert round(final_score_3, 2) == 73.5, f"Expected 73.5, got {final_score_3}"
    print_status("Test 3: Known score combination (80, 60, 40, 90) -> 73.5", True)

    # ==========================================================================
    # GROUP B: WEIGHT RENORMALIZATION TESTS
    # ==========================================================================
    print("\n--- GROUP B: WEIGHT RENORMALIZATION ---")

    # Case 4: Tools absent from JD -> weights: Skills 27.7778%, Responsibilities 33.3333%, Experience 38.8889%
    jd_no_tools = JobDescriptionObject(
        required_skills=["Python"],
        responsibilities=["Backend dev"],
        tools_and_technologies=[],
        experience_requirements=[ExperienceRequirement(preferred_domains=["Finance"])],
    )
    app_4 = engine.determine_category_applicability(jd_no_tools)
    assert app_4["tools_and_technologies"] == "not_applicable"
    assert app_4["required_skills"] == "applicable"
    assert app_4["responsibilities"] == "applicable"
    assert app_4["experience_relevance"] == "applicable"

    w_4 = engine.normalize_weights(app_4)
    assert w_4["tools_and_technologies"] == 0.0
    assert abs(w_4["required_skills"] - (0.25 / 0.90)) < 1e-4  # ~0.277778
    assert abs(w_4["responsibilities"] - (0.30 / 0.90)) < 1e-4  # ~0.333333
    assert abs(w_4["experience_relevance"] - (0.35 / 0.90)) < 1e-4  # ~0.388889
    assert abs(sum(w_4.values()) - 1.0) < 1e-6
    print_status("Test 4: Tools absent -> Renormalization to 27.78%, 33.33%, 38.89%", True)

    # Case 5: Skills absent from JD -> Redistribute among remaining
    # Base: Resp 0.30, Tools 0.10, Exp 0.35 -> sum = 0.75
    jd_no_skills = JobDescriptionObject(
        required_skills=[],
        responsibilities=["Coding"],
        tools_and_technologies=["Git"],
        experience_requirements=[ExperienceRequirement(preferred_domains=["Tech"])],
    )
    app_5 = engine.determine_category_applicability(jd_no_skills)
    assert app_5["required_skills"] == "not_applicable"
    w_5 = engine.normalize_weights(app_5)
    assert w_5["required_skills"] == 0.0
    assert abs(w_5["responsibilities"] - (0.30 / 0.75)) < 1e-4  # 0.40
    assert abs(w_5["tools_and_technologies"] - (0.10 / 0.75)) < 1e-4  # ~0.133333
    assert abs(w_5["experience_relevance"] - (0.35 / 0.75)) < 1e-4  # ~0.466667
    assert abs(sum(w_5.values()) - 1.0) < 1e-6
    print_status("Test 5: Skills absent -> Proportional redistribution to remaining categories", True)

    # Case 6: Multiple absent categories (e.g. only responsibilities and tools)
    jd_two_cats = JobDescriptionObject(
        required_skills=[],
        responsibilities=["Deploy"],
        tools_and_technologies=["AWS"],
        experience_requirements=[],
    )
    app_6 = engine.determine_category_applicability(jd_two_cats)
    w_6 = engine.normalize_weights(app_6)
    # Sum of 0.30 + 0.10 = 0.40 -> Resp 0.75, Tools 0.25
    assert abs(w_6["responsibilities"] - 0.75) < 1e-6
    assert abs(w_6["tools_and_technologies"] - 0.25) < 1e-6
    assert w_6["required_skills"] == 0.0
    assert w_6["experience_relevance"] == 0.0
    assert abs(sum(w_6.values()) - 1.0) < 1e-6
    print_status("Test 6: Multiple absent categories correctly normalized", True)

    # Case 7: No applicable categories -> No final score, status no_scorable_requirements
    jd_empty = JobDescriptionObject(
        required_skills=[],
        responsibilities=[],
        tools_and_technologies=[],
        experience_requirements=[],
    )
    res_7 = engine.score_candidate({"upload_id": "b", "filename": "f"}, jd_empty)
    assert res_7.status == "no_scorable_requirements"
    assert res_7.final_score is None
    print_status("Test 7: No applicable categories -> status 'no_scorable_requirements', final_score None", True)

    # Case 8: Normalized weights always sum to 1 within sensible floating point tolerance
    for combo in [
        {"required_skills": "applicable", "responsibilities": "applicable"},
        {"responsibilities": "applicable", "experience_relevance": "applicable"},
        {"tools_and_technologies": "applicable"},
        {"required_skills": "applicable", "tools_and_technologies": "applicable", "experience_relevance": "applicable"},
    ]:
        weights = engine.normalize_weights(combo)
        assert abs(sum(weights.values()) - 1.0) < 1e-6
    print_status("Test 8: Normalized weights sum to 1.0 across all subsets of applicable categories", True)

    # ==========================================================================
    # GROUP C: MISSING EVIDENCE AND ERROR HANDLING
    # ==========================================================================
    print("\n--- GROUP C: MISSING EVIDENCE & ERRORS ---")

    # Case 9: Applicable category with valid zero evidence receives score 0.0
    jd_req = JobDescriptionObject(
        required_skills=["Rust"],
        responsibilities=["Systems programming"],
        tools_and_technologies=["Linux"],
        experience_requirements=[ExperienceRequirement(preferred_domains=["Embedded"])],
    )
    match_zero_ev = {
        "upload_id": "b",
        "filename": "f",
        "exact_matching": {"total_required_skills": 1, "matched_required_skills": 0, "matches": []},
        "semantic_retrieval": {
            "responsibilities_retrieval": {"results": []},
            "tools_and_technologies_retrieval": {"results": []},
        },
        "experience_matching": {"experiences": []},
    }
    res_9 = engine.score_candidate(match_zero_ev, jd_req)
    assert res_9.status == "complete"
    assert res_9.final_score == 0.0
    assert res_9.breakdown["required_skills"].score == 0.0
    assert res_9.breakdown["responsibilities"].score == 0.0
    assert res_9.breakdown["tools_and_technologies"].score == 0.0
    assert res_9.breakdown["experience_relevance"].score == 0.0
    print_status("Test 9: Applicable category with zero candidate evidence receives score 0.0", True)

    # Case 10: Absent category does NOT reduce final score
    # Candidate scores 100 on applicable categories (skills, resp, exp) when tools is absent
    match_10 = {
        "upload_id": "b",
        "filename": "f",
        "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1, "matches": [{"required_skill": "Python", "matched": True}]},
        "semantic_retrieval": {
            "responsibilities_retrieval": {
                "results": [{"jd_item_index": 0, "matches": [{"similarity": 1.0}]}]
            },
            "tools_and_technologies_retrieval": {"results": []},
        },
        "experience_matching": {
            "experiences": [{"role": "Dev", "relevant": True, "relevance_score": 1.0}]
        },
    }
    res_10 = engine.score_candidate(match_10, jd_no_tools)
    assert res_10.status == "complete"
    assert res_10.final_score == 100.0, f"Expected 100.0, got {res_10.final_score}"
    assert res_10.breakdown["tools_and_technologies"].status == "not_applicable"
    assert res_10.breakdown["tools_and_technologies"].score is None
    print_status("Test 10: Absent category does not penalize score (candidate gets 100% on remaining)", True)

    # Case 11: Failed matching service is marked unavailable, not a valid zero
    match_failed_skills = {
        "upload_id": "b",
        "filename": "f",
        "exact_matching": None,  # Service crashed / failed
        "semantic_retrieval": {"responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}},
        "experience_matching": {"experiences": []},
    }
    res_11 = engine.score_candidate(match_failed_skills, jd_req)
    assert res_11.breakdown["required_skills"].status == "unavailable"
    assert res_11.breakdown["required_skills"].score is None
    assert res_11.status == "incomplete"
    assert res_11.final_score is None
    print_status("Test 11: Failed matching service is 'unavailable', candidate status 'incomplete'", True)

    # Case 12: Failed retrieval service marks overall score incomplete by default
    match_failed_retrieval = {
        "upload_id": "b",
        "filename": "f",
        "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1},
        "semantic_retrieval": None,  # Retrieval crashed
        "experience_matching": {"experiences": []},
    }
    res_12 = engine.score_candidate(match_failed_retrieval, jd_req)
    assert res_12.breakdown["responsibilities"].status == "unavailable"
    assert res_12.status == "incomplete"
    assert res_12.final_score is None
    print_status("Test 12: Failed retrieval service marks overall score incomplete by default", True)

    # Case 13: Empty resume evidence does NOT make JD category not applicable
    # JD has required skills; candidate has no skills listed -> status is complete with score 0
    res_13 = engine.score_candidate(
        {
            "upload_id": "b",
            "filename": "f",
            "exact_matching": {"total_required_skills": 1, "matched_required_skills": 0, "matches": []},
            "semantic_retrieval": {"responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}},
            "experience_matching": {"experiences": []},
        },
        jd_req,
    )
    assert res_13.breakdown["required_skills"].status == "complete"
    assert res_13.breakdown["required_skills"].score == 0.0
    print_status("Test 13: Empty resume evidence does not alter JD category applicability", True)

    # Case 14: Invalid or missing numeric values handled safely
    raw_sim_tests = [-0.5, 0.0, 0.6499, 0.65, 0.825, 1.0, 1.5]
    norm_results = [engine.normalize_similarity(s, 0.65) for s in raw_sim_tests]
    assert norm_results[0] == 0.0
    assert norm_results[1] == 0.0
    assert norm_results[2] == 0.0
    assert norm_results[3] == 0.0
    assert abs(norm_results[4] - 0.5) < 1e-4  # (0.825 - 0.65) / 0.35 = 0.5
    assert norm_results[5] == 1.0
    assert norm_results[6] == 1.0
    print_status("Test 14: Normalized similarity safely clamps below threshold, at threshold, and above 1.0", True)

    # ==========================================================================
    # GROUP D: EXPERIENCE-SPECIFIC TESTS
    # ==========================================================================
    print("\n--- GROUP D: EXPERIENCE-SPECIFIC TESTS ---")

    jd_3_domains = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(
                preferred_domains=["Payments", "Cloud Architecture", "Data Engineering"],
                minimum_years=3.0,
                maximum_years=7.0,
            )
        ]
    )

    # Case 15: Denominator is fixed number of JD experience criteria (3), not candidate job count
    # Candidate has 1 job supporting 1 domain with score 0.90
    exp_cand_1_job = {
        "experiences": [
            {
                "role": "Payment Engineer",
                "relevant": True,
                "relevance_score": 0.90,
            }
        ]
    }
    # With 3 criteria: (0.90 + 0.0 + 0.0) / 3 * 100 = 30.0
    score_15, status_15, tot_15, qual_15, _, _ = engine.calculate_experience_relevance_score(
        exp_cand_1_job,
        jd_3_domains,
        relevance_decisions=[{"experience_index": 0, "matched_domains": ["Payments"]}],
    )
    assert tot_15 == 3, f"Expected 3 criteria, got {tot_15}"
    assert abs(score_15 - 30.0) < 1e-4, f"Expected 30.0, got {score_15}"
    print_status("Test 15: Experience score denominator is number of JD criteria (3), not candidate job count", True)

    # Case 16: Candidate with 1 job vs Candidate with 5 jobs receive identical score when best evidence is identical
    # Candidate A: 1 job with Payments (0.90) -> score 30.0
    # Candidate B: 5 jobs, where best for Payments is 0.90, others 0.80, 0.70, etc. (all Payments or irrelevant) -> score 30.0
    exp_cand_5_jobs = {
        "experiences": [
            {"role": "Payment Lead", "relevant": True, "relevance_score": 0.90},
            {"role": "Payment Dev", "relevant": True, "relevance_score": 0.85},
            {"role": "Junior Dev", "relevant": True, "relevance_score": 0.50},
            {"role": "Tutor", "relevant": False, "relevance_score": 0.0},
            {"role": "Cashier", "relevant": False, "relevance_score": 0.0},
        ]
    }
    decisions_cand_b = [
        {"experience_index": 0, "matched_domains": ["Payments"]},
        {"experience_index": 1, "matched_domains": ["Payments"]},
        {"experience_index": 2, "matched_domains": ["Payments"]},
        {"experience_index": 3, "matched_domains": []},
        {"experience_index": 4, "matched_domains": []},
    ]
    score_16, _, _, _, _, _ = engine.calculate_experience_relevance_score(
        exp_cand_5_jobs,
        jd_3_domains,
        relevance_decisions=decisions_cand_b,
    )
    assert abs(score_16 - score_15) < 1e-4, f"Candidate with 5 jobs score {score_16} differs from 1 job score {score_15}"
    print_status("Test 16: 1 job vs 5 jobs with same best evidence receive identical score", True)

    # Case 17: Adding an unrelated experience does NOT reduce best evidence already selected
    exp_cand_added_unrelated = {
        "experiences": [
            {"role": "Payment Lead", "relevant": True, "relevance_score": 0.90},
            {"role": "Graphic Designer", "relevant": False, "relevance_score": 0.0},
        ]
    }
    score_17, _, _, _, _, _ = engine.calculate_experience_relevance_score(
        exp_cand_added_unrelated,
        jd_3_domains,
        relevance_decisions=[
            {"experience_index": 0, "matched_domains": ["Payments"]},
            {"experience_index": 1, "matched_domains": []},
        ],
    )
    assert abs(score_17 - score_15) < 1e-4
    print_status("Test 17: Adding unrelated experience does not reduce criterion best score", True)

    # Case 18: Additional relevant evidence can improve score when selected best evidence becomes stronger
    # Suppose candidate adds an experience in Cloud Architecture (0.80)
    exp_cand_stronger = {
        "experiences": [
            {"role": "Payment Lead", "relevant": True, "relevance_score": 0.90},
            {"role": "Cloud Architect", "relevant": True, "relevance_score": 0.80},
        ]
    }
    # With (0.90 + 0.80 + 0.0) / 3 * 100 = 56.6667
    score_18, _, _, qual_18, _, _ = engine.calculate_experience_relevance_score(
        exp_cand_stronger,
        jd_3_domains,
        relevance_decisions=[
            {"experience_index": 0, "matched_domains": ["Payments"]},
            {"experience_index": 1, "matched_domains": ["Cloud Architecture"]},
        ],
    )
    assert abs(score_18 - 56.6667) < 1e-3, f"Expected 56.67, got {score_18}"
    assert qual_18 == 2
    assert score_18 > score_15
    print_status("Test 18: Supporting additional criterion improves experience score (56.67 vs 30.0)", True)

    # Case 19: Experience scores stay strictly between 0 and 100
    assert 0.0 <= score_15 <= 100.0
    assert 0.0 <= score_18 <= 100.0
    # Perfect candidate: all 3 criteria 1.0 -> 100.0
    exp_perfect = {
        "experiences": [
            {"role": "Lead", "relevant": True, "relevance_score": 1.0},
        ]
    }
    score_19, _, _, _, _, _ = engine.calculate_experience_relevance_score(
        exp_perfect,
        jd_3_domains,
        relevance_decisions=[
            {"experience_index": 0, "matched_domains": ["Payments", "Cloud Architecture", "Data Engineering"]},
        ],
    )
    assert score_19 == 100.0
    print_status("Test 19: Experience scores stay strictly between 0 and 100", True)

    # Case 20: The minimum-years check is separate from the relevance score
    # Candidate with 10 years experience vs 2 years experience with same relevance get SAME experience score
    match_2_years = {
        "upload_id": "b",
        "filename": "f2",
        "exact_matching": {"total_required_skills": 0, "matched_required_skills": 0},
        "semantic_retrieval": {"responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}},
        "experience_matching": {
            "minimum_years": 3.0,
            "relevant_duration_years": 2.0,
            "minimum_duration_satisfied": False,
            "experiences": [{"role": "Dev", "relevant": True, "relevance_score": 0.90}],
        },
    }
    match_10_years = {
        "upload_id": "b",
        "filename": "f10",
        "exact_matching": {"total_required_skills": 0, "matched_required_skills": 0},
        "semantic_retrieval": {"responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}},
        "experience_matching": {
            "minimum_years": 3.0,
            "relevant_duration_years": 10.0,
            "minimum_duration_satisfied": True,
            "experiences": [{"role": "Dev", "relevant": True, "relevance_score": 0.90}],
        },
    }
    dec_single = [{"experience_index": 0, "matched_domains": ["Payments"]}]
    res_2_yrs = engine.score_candidate(match_2_years, jd_3_domains, dec_single)
    res_10_yrs = engine.score_candidate(match_10_years, jd_3_domains, dec_single)

    assert res_2_yrs.breakdown["experience_relevance"].score == res_10_yrs.breakdown["experience_relevance"].score
    assert res_2_yrs.experience_diagnostic.minimum_duration_satisfied is False
    assert res_10_yrs.experience_diagnostic.minimum_duration_satisfied is True
    print_status("Test 20: Minimum years check is diagnostic and separate from relevance score", True)

    # Case 21: Exceeding the JD maximum experience does not automatically reduce relevance score
    match_exceeding_max = {
        "upload_id": "b",
        "filename": "f_over",
        "exact_matching": {"total_required_skills": 0, "matched_required_skills": 0},
        "semantic_retrieval": {"responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}},
        "experience_matching": {
            "maximum_years": 7.0,
            "relevant_duration_years": 15.0,
            "maximum_duration_exceeded": True,
            "experiences": [{"role": "Dev", "relevant": True, "relevance_score": 0.90}],
        },
    }
    res_exceeding = engine.score_candidate(match_exceeding_max, jd_3_domains, dec_single)
    assert res_exceeding.breakdown["experience_relevance"].score == res_10_yrs.breakdown["experience_relevance"].score
    assert res_exceeding.experience_diagnostic.maximum_duration_exceeded is True
    print_status("Test 21: Exceeding maximum experience does not penalize relevance score", True)

    # Case 22: Missing or invalid dates do not silently become zero years
    match_missing_dates = {
        "upload_id": "b",
        "filename": "f_dates",
        "exact_matching": {"total_required_skills": 0, "matched_required_skills": 0},
        "semantic_retrieval": {"responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}},
        "experience_matching": {
            "diagnostic_status": "dates_missing_or_unparseable",
            "diagnostic_message": "Relevant experience found, but dates are missing.",
            "relevant_duration_years": 0.0,
            "experiences": [{"role": "Dev", "relevant": True, "relevance_score": 0.90, "date_status": "missing_dates"}],
        },
    }
    res_dates = engine.score_candidate(match_missing_dates, jd_3_domains, dec_single)
    assert res_dates.experience_diagnostic.diagnostic_status == "dates_missing_or_unparseable"
    assert any("dates are missing" in w for w in res_dates.warnings)
    print_status("Test 22: Missing dates recorded transparently as diagnostic, not treated as silent 0 years", True)

    # Case 23: Do not create arbitrary top-three experience limits (evaluates all experiences)
    exp_cand_6_jobs = {
        "experiences": [
            {"role": "Job 1", "relevant": False, "relevance_score": 0.0},
            {"role": "Job 2", "relevant": False, "relevance_score": 0.0},
            {"role": "Job 3", "relevant": False, "relevance_score": 0.0},
            {"role": "Job 4", "relevant": True, "relevance_score": 0.95},  # Beyond top 3
        ]
    }
    score_23, _, _, qual_23, _, _ = engine.calculate_experience_relevance_score(
        exp_cand_6_jobs,
        jd_3_domains,
        relevance_decisions=[
            {"experience_index": 0, "matched_domains": []},
            {"experience_index": 1, "matched_domains": []},
            {"experience_index": 2, "matched_domains": []},
            {"experience_index": 3, "matched_domains": ["Payments"]},
        ],
    )
    # The 4th job must be evaluated and selected!
    assert abs(score_23 - (0.95 / 3 * 100)) < 1e-3, f"Expected 31.67, got {score_23}"
    assert qual_23 == 1
    print_status("Test 23: 4th experience beyond top 3 is fully evaluated and contributes to best evidence", True)

    # ==========================================================================
    # GROUP F: AUDIT FIX TESTS (MATCHED_DOMAINS SEGREGATION & BACKWARD COMPATIBILITY)
    # ==========================================================================
    print("\n--- GROUP F: MATCHED_DOMAINS SEGREGATION & COMPATIBILITY ---")

    jd_fintech_health = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(
                preferred_domains=["Fintech", "Healthcare"],
                minimum_years=2.0,
            )
        ]
    )

    # Test 31 (Requirement 6): Fintech-only experience must NOT automatically qualify for Healthcare
    cand_fintech_only = {
        "experiences": [
            CandidateExperienceItem(
                experience_index=0,
                role="Payment Gateway Engineer",
                company="Fintech Co",
                decision="RELEVANT",
                relevant=True,
                matched_domains=["Fintech"],
            )
        ]
    }
    score_31, _, tot_31, qual_31, evid_31, _ = engine.calculate_experience_relevance_score(
        cand_fintech_only,
        jd_fintech_health,
    )
    assert tot_31 == 2, f"Expected 2 criteria, got {tot_31}"
    assert qual_31 == 1, f"Expected 1 qualifying criterion, got {qual_31}"
    assert abs(score_31 - 50.0) < 1e-4, f"Expected 50.0, got {score_31}"
    assert evid_31[0]["criterion"] == "Fintech" and evid_31[0]["qualifies"] is True
    assert evid_31[1]["criterion"] == "Healthcare" and evid_31[1]["qualifies"] is False
    print_status("Test 31: Fintech-only experience qualifies only for Fintech and NOT Healthcare (50.0/100)", True)

    # Test 32 (Requirement 7): Experience explicitly supporting both domains contributes to both
    cand_both_domains = {
        "experiences": [
            CandidateExperienceItem(
                experience_index=0,
                role="HealthTech Payments Lead",
                company="MedPay Inc",
                decision="RELEVANT",
                relevant=True,
                matched_domains=["Fintech", "Healthcare"],
            )
        ]
    }
    score_32, _, tot_32, qual_32, evid_32, _ = engine.calculate_experience_relevance_score(
        cand_both_domains,
        jd_fintech_health,
    )
    assert tot_32 == 2
    assert qual_32 == 2
    assert abs(score_32 - 100.0) < 1e-4, f"Expected 100.0, got {score_32}"
    assert evid_32[0]["qualifies"] is True and evid_32[1]["qualifies"] is True
    print_status("Test 32: Experience explicitly supporting both domains contributes to both (100.0/100)", True)

    # Test 33 (Requirement 8): Empty matched_domains list cannot inflate experience score
    cand_empty_domains = {
        "experiences": [
            CandidateExperienceItem(
                experience_index=0,
                role="General Developer",
                company="Startup",
                decision="RELEVANT",
                relevant=True,
                matched_domains=[],  # Evaluated, but zero domains matched
            )
        ]
    }
    score_33, _, tot_33, qual_33, evid_33, _ = engine.calculate_experience_relevance_score(
        cand_empty_domains,
        jd_fintech_health,
    )
    assert tot_33 == 2
    assert qual_33 == 0, f"Expected 0 qualifying criteria, got {qual_33}"
    assert score_33 == 0.0, f"Expected 0.0, got {score_33}"
    assert evid_33[0]["qualifies"] is False and evid_33[1]["qualifies"] is False
    print_status("Test 33: Empty matched_domains list receives 0.0 (fallback cannot inflate score)", True)

    # Test 34 (Requirement 5): Safe backward compatibility for legacy records genuinely lacking matched_domains
    # Subcase A: Single domain in JD -> general relevance maps to single domain
    jd_single_domain = JobDescriptionObject(
        experience_requirements=[ExperienceRequirement(preferred_domains=["Fintech"])]
    )
    legacy_single = {
        "experiences": [
            {"experience_index": 0, "role": "Software Engineer", "relevant": True, "decision": "RELEVANT"}
        ]
    }
    score_34a, _, _, qual_34a, evid_34a, _ = engine.calculate_experience_relevance_score(
        legacy_single,
        jd_single_domain,
    )
    assert qual_34a == 1
    assert score_34a == 100.0
    assert "Legacy record lacks domain tags" in (evid_34a[0]["reason"] or "")

    # Subcase B: Multiple domains in JD -> does not fabricate matches across domains without explicit text
    legacy_multi = {
        "experiences": [
            {"experience_index": 0, "role": "General Engineer", "relevant": True, "decision": "RELEVANT"}
        ]
    }
    score_34b, _, _, qual_34b, evid_34b, _ = engine.calculate_experience_relevance_score(
        legacy_multi,
        jd_fintech_health,
    )
    assert qual_34b == 0
    assert score_34b == 0.0
    # ==========================================================================
    # GROUP G: LIVE AUDIT DEFECT REGRESSION TESTS (CASES 35–41)
    # ==========================================================================
    print("\n--- GROUP G: LIVE AUDIT DEFECT REGRESSION TESTS ---")

    jd_multi_tools = JobDescriptionObject(
        tools_and_technologies=["Python", "PyTorch", "Docker"],
        responsibilities=["Build distributed services"],
    )

    # Test 35: Project retrieval returning valid evidence
    retrieval_valid_tools = {
        "tools_and_technologies_retrieval": {
            "results": [
                {
                    "jd_item_index": 0,
                    "jd_text": "Tool or technology: Python",
                    "matches": [{"similarity": 0.85, "resume_text": "Project: ML Pipeline in Python", "resume_section": "projects"}],
                },
                {
                    "jd_item_index": 1,
                    "jd_text": "Tool or technology: PyTorch",
                    "matches": [{"similarity": 0.80, "resume_text": "Project: Vision Model in PyTorch", "resume_section": "projects"}],
                },
                {
                    "jd_item_index": 2,
                    "jd_text": "Tool or technology: Docker",
                    "matches": [],  # Docker not used in projects
                },
            ]
        }
    }
    score_35, stat_35, tot_35, qual_35, evid_35, note_35 = engine.calculate_tools_score(
        retrieval_valid_tools,
        jd_multi_tools.tools_and_technologies,
    )
    assert stat_35 == "complete", f"Expected complete, got {stat_35}"
    assert tot_35 == 3
    assert qual_35 == 2
    assert score_35 > 0.0
    assert evid_35[0]["qualifies"] is True and evid_35[0]["best_matching_section"] == "projects"
    assert evid_35[1]["qualifies"] is True and evid_35[1]["best_matching_section"] == "projects"
    assert evid_35[2]["qualifies"] is False and evid_35[2]["best_matching_passage"] is None
    print_status("Test 35: Project retrieval returning valid evidence scores correctly", True)

    # Test 36: Project retrieval succeeding with no qualifying evidence (e.g. no projects or all sub-threshold)
    retrieval_no_qual = {
        "tools_and_technologies_retrieval": {
            "results": [
                {"jd_item_index": 0, "jd_text": "Tool or technology: Python", "matches": []},
                {"jd_item_index": 1, "jd_text": "Tool or technology: PyTorch", "matches": []},
                {"jd_item_index": 2, "jd_text": "Tool or technology: Docker", "matches": []},
            ]
        }
    }
    score_36, stat_36, tot_36, qual_36, evid_36, note_36 = engine.calculate_tools_score(
        retrieval_no_qual,
        jd_multi_tools.tools_and_technologies,
    )
    assert stat_36 == "complete", f"Expected complete for valid empty evidence, got {stat_36}"
    assert score_36 == 0.0
    assert qual_36 == 0
    assert note_36 is not None and "No qualifying project evidence found" in note_36
    print_status("Test 36: Project retrieval succeeding with no qualifying evidence yields valid score 0.0", True)

    # Test 37: Missing/corrupt embeddings and retrieval exceptions marked unavailable
    # Subcase A: error flag in retrieval payload
    retrieval_error = {"error": "BGE embedding model connection failed"}
    score_37a, stat_37a, _, _, _, note_37a = engine.calculate_tools_score(
        retrieval_error,
        jd_multi_tools.tools_and_technologies,
    )
    assert stat_37a == "unavailable"
    assert score_37a is None

    # Subcase B: tools retrieval section missing or failed (None) when JD defines tools
    retrieval_missing_records = {
        "tools_and_technologies_retrieval": None
    }
    score_37b, stat_37b, _, _, _, note_37b = engine.calculate_tools_score(
        retrieval_missing_records,
        jd_multi_tools.tools_and_technologies,
    )
    assert stat_37b == "unavailable"
    assert score_37b is None

    # Subcase C: Candidate score marks overall status incomplete when retrieval unavailable
    cand_incomplete_match = {
        "upload_id": "b1",
        "filename": "failed_candidate.pdf",
        "jd_id": "jd1",
        "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1, "matches": [{"required_skill": "Python", "matched": True}]},
        "semantic_retrieval": retrieval_error,
        "experience_matching": {"experiences": []},
    }
    cand_res_37 = engine.score_candidate(cand_incomplete_match, jd_multi_tools)
    assert cand_res_37.status == "incomplete"
    assert cand_res_37.final_score is None
    print_status("Test 37: Missing/corrupt embeddings and retrieval exceptions safely produce unavailable/incomplete", True)

    # Test 38: Explicit matched-domain attribution across 10 JD criteria
    ten_domains = [
        "Consumer Products", "Life Sciences", "Financial Services", "Technology",
        "Healthcare", "Manufacturing", "Retail", "Telecommunications", "Energy", "Education"
    ]
    jd_10_domains = JobDescriptionObject(
        experience_requirements=[ExperienceRequirement(preferred_domains=ten_domains)]
    )
    cand_2_of_10 = {
        "experiences": [
            CandidateExperienceItem(
                experience_index=0,
                role="Tech Lead",
                company="Tech Corp",
                decision="RELEVANT",
                relevant=True,
                relevance_score=1.0,
                matched_domains=["Technology"],
            ),
            CandidateExperienceItem(
                experience_index=1,
                role="Brand Analyst",
                company="CPG Goods",
                decision="RELEVANT",
                relevant=True,
                relevance_score=1.0,
                matched_domains=["Consumer Products"],
            ),
        ]
    }
    score_38, stat_38, tot_38, qual_38, evid_38, _ = engine.calculate_experience_relevance_score(
        cand_2_of_10,
        jd_10_domains,
    )
    assert tot_38 == 10
    assert qual_38 == 2, f"Expected exactly 2 qualifying criteria, got {qual_38}"
    # 2 domains supported at 1.0 out of 10 criteria -> 100 * (1.0 + 1.0) / 10 = 20.0
    assert abs(score_38 - 20.0) < 1e-4, f"Expected 20.0, got {score_38}"
    evid_map_38 = {e["criterion"]: e["qualifies"] for e in evid_38}
    assert evid_map_38["Technology"] is True
    assert evid_map_38["Consumer Products"] is True
    assert evid_map_38["Financial Services"] is False
    assert evid_map_38["Life Sciences"] is False
    print_status("Test 38: Explicit matched-domain attribution restricts evidence solely to matching domains", True)

    # Test 39: Legacy experience records without domain metadata in multi-domain JD never fabricate matches
    legacy_text_with_keywords = {
        "experiences": [
            {
                "experience_index": 0,
                "role": "General Developer in Technology",
                "company": "Financial Services Group",
                "description": "Worked on consumer products and life sciences apps",
                "relevant": True,
                "decision": "RELEVANT",
                # Note: No matched_domains key at all (legacy record)
            }
        ]
    }
    score_39, stat_39, tot_39, qual_39, evid_39, _ = engine.calculate_experience_relevance_score(
        legacy_text_with_keywords,
        jd_10_domains,
    )
    # Even though text contains keyword strings, legacy records must NOT fabricate domain matches
    assert qual_39 == 0, f"Expected 0 qualifying criteria for legacy multi-domain, got {qual_39}"
    assert score_39 == 0.0
    assert all(e["qualifies"] is False for e in evid_39)
    print_status("Test 39: Legacy experience records in multi-domain JD do not fabricate matches via text search", True)

    # Test 40: Exact responsibilities score normalization and weighted contribution verification
    # 11 JD responsibilities, 1 qualifying criterion at raw similarity 0.652
    jd_11_resp = JobDescriptionObject(
        responsibilities=[f"Responsibility {i}" for i in range(11)]
    )
    norm_expected = round((0.652 - 0.65) / 0.35, 4)  # ~0.0057
    retrieval_11_resp = {
        "responsibilities_retrieval": {
            "results": [
                {
                    "jd_item_index": 0,
                    "jd_text": "Responsibility: Responsibility 0",
                    "matches": [{"similarity": 0.652, "resume_text": "Did some tasks", "resume_section": "experience"}],
                }
            ] + [
                {
                    "jd_item_index": i,
                    "jd_text": f"Responsibility: Responsibility {i}",
                    "matches": [{"similarity": 0.50, "resume_text": "Irrelevant", "resume_section": "experience"}],
                }
                for i in range(1, 11)
            ]
        }
    }
    score_40, stat_40, tot_40, qual_40, evid_40, _ = engine.calculate_responsibilities_score(
        retrieval_11_resp,
        jd_11_resp.responsibilities,
    )
    assert tot_40 == 11
    assert qual_40 == 1
    # Component score is mean normalized score * 100: (0.005714 / 11) * 100 ~ 0.0519
    assert 0.05 <= score_40 <= 0.06
    # In candidate scoring, component_scores must round cleanly to 2 decimal places (0.05)
    cand_match_40 = {
        "upload_id": "b1",
        "filename": "resp_cand.pdf",
        "jd_id": "jd1",
        "exact_matching": None,
        "semantic_retrieval": retrieval_11_resp,
        "experience_matching": None,
    }
    cand_res_40 = engine.score_candidate(cand_match_40, jd_11_resp)
    assert cand_res_40.component_scores["responsibilities"] == 0.05
    assert cand_res_40.breakdown["responsibilities"].score == 0.05
    assert cand_res_40.breakdown["responsibilities"].weighted_contribution == round(1.0 * score_40, 4)
    print_status("Test 40: Responsibilities normalization, rounding, and weighted contribution verified mathematically", True)

    # Test 41: Incomplete candidate handling and deterministic batch ranking
    cand_a = CandidateRankingResult(
        upload_id="b1", filename="cand_a.pdf", jd_id="j1", status="complete", final_score=85.0,
        component_scores={}, breakdown={},
    )
    cand_b = CandidateRankingResult(
        upload_id="b1", filename="cand_b.pdf", jd_id="j1", status="incomplete", final_score=None,
        component_scores={}, breakdown={},
    )
    cand_c = CandidateRankingResult(
        upload_id="b1", filename="cand_c.pdf", jd_id="j1", status="complete", final_score=65.0,
        component_scores={}, breakdown={},
    )
    ranked_41, unranked_41 = engine.rank_candidates([cand_a, cand_b, cand_c])
    assert len(ranked_41) == 2
    assert ranked_41[0].filename == "cand_a.pdf" and ranked_41[0].rank == 1
    assert ranked_41[1].filename == "cand_c.pdf" and ranked_41[1].rank == 2
    assert len(unranked_41) == 1
    assert unranked_41[0].filename == "cand_b.pdf" and unranked_41[0].rank is None
    print_status("Test 41: Incomplete candidate cleanly separated from ranked list and unranked", True)

    # ==============================================================================
    # GROUP H: FINDINGS 1, 2, 4 REGRESSION TESTS (Pydantic retrieval failures, skill count reconciliation, experience failure & attribution)
    # ==============================================================================
    print("\n--- GROUP H: AUDIT FINDINGS 1, 2, 4 REGRESSION TESTS ---")

    # Test 42: Finding 1 - Responsibilities retrieval failure handling (all 6 cases for Pydantic & dict)
    jd_resp = ["Develop distributed systems", "Lead ML research"]

    # 1. Valid retrieval with qualifying evidence (> 0.65)
    pyd_case1 = SemanticRetrievalResult(
        top_k=5,
        responsibilities_retrieval=SemanticSectionRetrieval(
            top_k=5,
            results=[
                SemanticRetrievalRequirementResult(
                    jd_item_index=0,
                    jd_text="Develop distributed systems",
                    matches=[SemanticEvidenceMatchItem(similarity=0.85, resume_text="Built distributed Kafka pipelines", resume_section="experience")]
                ),
                SemanticRetrievalRequirementResult(
                    jd_item_index=1,
                    jd_text="Lead ML research",
                    matches=[SemanticEvidenceMatchItem(similarity=0.50, resume_text="Wrote scripts", resume_section="experience")]
                )
            ]
        )
    )
    score_p1, stat_p1, tot_p1, qual_p1, _, _ = engine.calculate_responsibilities_score(pyd_case1, jd_resp)
    assert stat_p1 == "complete" and qual_p1 == 1 and score_p1 > 0.0

    # 2. Valid retrieval with no qualifying evidence (< 0.65) -> score 0, status complete
    pyd_case2 = SemanticRetrievalResult(
        top_k=5,
        responsibilities_retrieval=SemanticSectionRetrieval(
            top_k=5,
            results=[
                SemanticRetrievalRequirementResult(
                    jd_item_index=0,
                    jd_text="Develop distributed systems",
                    matches=[SemanticEvidenceMatchItem(similarity=0.55, resume_text="Text", resume_section="experience")]
                )
            ]
        )
    )
    score_p2, stat_p2, tot_p2, qual_p2, _, note_p2 = engine.calculate_responsibilities_score(pyd_case2, jd_resp)
    assert stat_p2 == "complete" and qual_p2 == 0 and score_p2 == 0.0 and note_p2 is not None

    # 3. Valid retrieval with an empty results list: score 0, status complete (service succeeded)
    pyd_case3 = SemanticRetrievalResult(
        top_k=5,
        responsibilities_retrieval=SemanticSectionRetrieval(top_k=5, results=[])
    )
    score_p3, stat_p3, tot_p3, qual_p3, _, _ = engine.calculate_responsibilities_score(pyd_case3, jd_resp)
    assert stat_p3 == "complete" and qual_p3 == 0 and score_p3 == 0.0

    # 4. Missing section result: unavailable (responsibilities_retrieval is None)
    pyd_case4 = SemanticRetrievalResult(top_k=5, responsibilities_retrieval=None)
    score_p4, stat_p4, tot_p4, qual_p4, _, note_p4 = engine.calculate_responsibilities_score(pyd_case4, jd_resp)
    assert stat_p4 == "unavailable" and score_p4 is None and qual_p4 == 0 and "missing or unavailable" in note_p4

    # Dict representation of missing section
    dict_case4 = {"top_k": 5}
    score_d4, stat_d4, _, _, _, note_d4 = engine.calculate_responsibilities_score(dict_case4, jd_resp)
    assert stat_d4 == "unavailable" and score_d4 is None and "missing or unavailable" in note_d4

    # 5. Section result with explicit failed status or error: unavailable
    pyd_case5 = SemanticRetrievalResult(
        top_k=5,
        responsibilities_retrieval=SemanticSectionRetrieval(
            top_k=5,
            results=[],
            status="failed",
            error="Embedding inference failure"
        )
    )
    score_p5, stat_p5, _, _, _, note_p5 = engine.calculate_responsibilities_score(pyd_case5, jd_resp)
    assert stat_p5 == "unavailable" and score_p5 is None and "failed" in note_p5

    dict_case5 = {
        "responsibilities_retrieval": {
            "status": "failed",
            "error": "Timeout generating embeddings",
            "results": []
        }
    }
    score_d5, stat_d5, _, _, _, note_d5 = engine.calculate_responsibilities_score(dict_case5, jd_resp)
    assert stat_d5 == "unavailable" and score_d5 is None and "Timeout" in note_d5

    # 6. Missing/corrupt embeddings or an actual retrieval exception: unavailable/incomplete
    pyd_case6 = SemanticRetrievalResult(top_k=5, status="failed", error="Database connection aborted")
    score_p6, stat_p6, _, _, _, note_p6 = engine.calculate_responsibilities_score(pyd_case6, jd_resp)
    assert stat_p6 == "unavailable" and score_p6 is None and "aborted" in note_p6

    dict_case6 = {"status": "failed", "error": "Corrupt embedding vector"}
    score_d6, stat_d6, _, _, _, note_d6 = engine.calculate_responsibilities_score(dict_case6, jd_resp)
    assert stat_d6 == "unavailable" and score_d6 is None and "Corrupt" in note_d6
    print_status("Test 42: Finding 1 - Responsibilities retrieval failure handling (all 6 cases for Pydantic & dict)", True)

    # Test 43: Finding 1 - Tools & Technologies retrieval failure handling (all 6 cases for Pydantic & dict)
    jd_tools = ["PyTorch", "Kubernetes", "Redis"]

    # 1. Valid retrieval with qualifying evidence
    pyd_tools_1 = SemanticRetrievalResult(
        top_k=5,
        tools_and_technologies_retrieval=SemanticSectionRetrieval(
            top_k=5,
            results=[
                SemanticRetrievalRequirementResult(
                    jd_item_index=0,
                    jd_text="PyTorch",
                    matches=[SemanticEvidenceMatchItem(similarity=0.88, resume_text="Project with PyTorch", resume_section="projects")]
                )
            ]
        )
    )
    score_t1, stat_t1, tot_t1, qual_t1, _, _ = engine.calculate_tools_score(pyd_tools_1, jd_tools)
    assert stat_t1 == "complete" and qual_t1 == 1 and score_t1 > 0.0

    # 2. Valid retrieval with no qualifying evidence (< 0.65)
    pyd_tools_2 = SemanticRetrievalResult(
        top_k=5,
        tools_and_technologies_retrieval=SemanticSectionRetrieval(
            top_k=5,
            results=[
                SemanticRetrievalRequirementResult(
                    jd_item_index=0,
                    jd_text="PyTorch",
                    matches=[SemanticEvidenceMatchItem(similarity=0.52, resume_text="Used Python", resume_section="projects")]
                )
            ]
        )
    )
    score_t2, stat_t2, _, qual_t2, _, _ = engine.calculate_tools_score(pyd_tools_2, jd_tools)
    assert stat_t2 == "complete" and qual_t2 == 0 and score_t2 == 0.0

    # 3. Valid retrieval with empty results list (candidate has 0 projects, retrieval succeeded cleanly)
    pyd_tools_3 = SemanticRetrievalResult(
        top_k=5,
        tools_and_technologies_retrieval=SemanticSectionRetrieval(top_k=5, results=[])
    )
    score_t3, stat_t3, _, qual_t3, _, _ = engine.calculate_tools_score(pyd_tools_3, jd_tools)
    assert stat_t3 == "complete" and qual_t3 == 0 and score_t3 == 0.0

    # 4. Missing tools section result: unavailable
    pyd_tools_4 = SemanticRetrievalResult(top_k=5, tools_and_technologies_retrieval=None)
    score_t4, stat_t4, _, _, _, note_t4 = engine.calculate_tools_score(pyd_tools_4, jd_tools)
    assert stat_t4 == "unavailable" and score_t4 is None and "missing or unavailable" in note_t4

    dict_tools_4 = {"top_k": 5}
    score_dt4, stat_dt4, _, _, _, note_dt4 = engine.calculate_tools_score(dict_tools_4, jd_tools)
    assert stat_dt4 == "unavailable" and score_dt4 is None and "missing or unavailable" in note_dt4

    # 5. Section result with explicit failed status or error: unavailable
    pyd_tools_5 = SemanticRetrievalResult(
        top_k=5,
        tools_and_technologies_retrieval=SemanticSectionRetrieval(
            top_k=5,
            results=[],
            status="failed",
            error="Tools embedding service down"
        )
    )
    score_t5, stat_t5, _, _, _, note_t5 = engine.calculate_tools_score(pyd_tools_5, jd_tools)
    assert stat_t5 == "unavailable" and score_t5 is None and "Tools embedding" in note_t5

    # 6. Corrupt embeddings or retrieval exception: unavailable
    dict_tools_6 = {"status": "failed", "error": "Corrupt project embeddings"}
    score_dt6, stat_dt6, _, _, _, note_dt6 = engine.calculate_tools_score(dict_tools_6, jd_tools)
    assert stat_dt6 == "unavailable" and score_dt6 is None and "Corrupt" in note_dt6
    print_status("Test 43: Finding 1 - Tools retrieval failure handling (all 6 cases for Pydantic & dict)", True)

    # Test 44: Finding 2 - Skill count and evidence consistency
    jd_skills = ["Python", "FastAPI", "Docker", "Kubernetes"]

    # Case A: Upstream count claims 4 matches, but evidence list only contains 2 matched items
    inconsistent_matching = {
        "total_required_skills": 4,
        "matched_required_skills": 4,  # Upstream inflated count
        "unmatched_required_skills": 0,
        "matches": [
            {"required_skill": "Python", "matched": True, "resume_skill": "Python", "match_type": "exact"},
            {"required_skill": "FastAPI", "matched": True, "resume_skill": "FastAPI", "match_type": "exact"},
            {"required_skill": "Docker", "matched": False, "resume_skill": None, "match_type": None},
            {"required_skill": "Kubernetes", "matched": False, "resume_skill": None, "match_type": None},
        ]
    }
    score_44, stat_44, tot_44, qual_44, evid_44, note_44 = engine.calculate_required_skills_score(
        inconsistent_matching,
        jd_skills,
    )
    # Score must be computed strictly from the 2 validated matches: (2 / 4) * 100 = 50.0
    assert abs(score_44 - 50.0) < 1e-4, f"Expected reconciled score 50.0, got {score_44}"
    assert qual_44 == 2, f"Expected 2 qualifying criteria, got {qual_44}"
    assert sum(1 for e in evid_44 if e["matched"] is True) == qual_44
    assert note_44 is not None and "reconciled to match validated evidence" in note_44

    # Case B: Required skills matching service technical error / failure
    err_skills_dict = {"status": "failed", "error": "Ollama LLM service unavailable"}
    score_44b, stat_44b, _, qual_44b, _, note_44b = engine.calculate_required_skills_score(
        err_skills_dict,
        jd_skills,
    )
    assert stat_44b == "unavailable" and score_44b is None and qual_44b == 0 and "Ollama LLM" in note_44b

    err_skills_pyd = ExactMatchingResult(
        total_required_skills=4,
        matched_required_skills=0,
        unmatched_required_skills=4,
        status="failed",
        error="LLM context window exceeded"
    )
    score_44c, stat_44c, _, qual_44c, _, note_44c = engine.calculate_required_skills_score(
        err_skills_pyd,
        jd_skills,
    )
    assert stat_44c == "unavailable" and score_44c is None and qual_44c == 0 and "context window" in note_44c
    print_status("Test 44: Finding 2 - Skill count and evidence consistency & failure handling verified", True)

    # Test 45: Finding 4 - Experience matching technical failures & domain attribution
    jd_exp_obj = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(preferred_domains=["Fintech", "Healthcare"])
        ]
    )

    # Case A: Technical failure in experience matching service returns unavailable, not fabricated zero
    err_exp_dict = {"status": "failed", "error": "LLM classification connection timeout"}
    score_45a, stat_45a, tot_45a, qual_45a, _, note_45a = engine.calculate_experience_relevance_score(
        err_exp_dict,
        jd_exp_obj,
    )
    assert stat_45a == "unavailable" and score_45a is None and "timeout" in note_45a

    err_exp_pyd = ExperienceMatchingResult(
        status="failed",
        error="Model worker crashed"
    )
    score_45b, stat_45b, _, _, _, note_45b = engine.calculate_experience_relevance_score(
        err_exp_pyd,
        jd_exp_obj,
    )
    assert stat_45b == "unavailable" and score_45b is None and "crashed" in note_45b

    # Case B: Empty matched_domains list ([]) never qualifies and receives score 0.0
    empty_domains_exp = ExperienceMatchingResult(
        experiences=[
            CandidateExperienceItem(
                experience_index=0,
                role="General Developer",
                company="Startup",
                relevant=True,
                decision="RELEVANT",
                matched_domains=[],  # Evaluated, but zero domains matched
            )
        ]
    )
    score_45c, stat_45c, tot_45c, qual_45c, evid_45c, _ = engine.calculate_experience_relevance_score(
        empty_domains_exp,
        jd_exp_obj,
    )
    assert stat_45c == "complete" and qual_45c == 0 and score_45c == 0.0
    assert evid_45c[0]["qualifies"] is False and evid_45c[1]["qualifies"] is False

    # Case C: Legacy record lacking domain metadata in multi-domain JD receives 0.0 and cannot fabricate matches
    legacy_multi = {
        "experiences": [
            {"experience_index": 0, "role": "Fullstack Dev", "relevant": True, "decision": "RELEVANT"}
        ]
    }
    score_45d, stat_45d, tot_45d, qual_45d, evid_45d, _ = engine.calculate_experience_relevance_score(
        legacy_multi,
        jd_exp_obj,
    )
    assert stat_45d == "complete" and qual_45d == 0 and score_45d == 0.0
    assert "cannot attribute general relevance to multi-domain" in evid_45d[0]["reason"]
    print_status("Test 45: Finding 4 - Experience matching technical failure & strict domain attribution verified", True)

    # ==============================================================================
    # Test 46: Finding 1 — Required Skills LLM failure propagation to ranking pipeline
    # ==============================================================================
    jd_skills_obj = JobDescriptionObject(
        required_skills=["Python", "FastAPI"],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    # 1. Valid retrieval with qualifying evidence
    valid_exact = ExactMatchingResult(
        total_required_skills=2,
        matched_required_skills=2,
        unmatched_required_skills=0,
        status="completed",
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=True, resume_skill="Python"),
            ExactSkillMatchItem(required_skill="FastAPI", matched=True, resume_skill="FastAPI"),
        ]
    )
    cand_valid = engine.score_candidate(
        match_result={
            "upload_id": "b1",
            "filename": "cand1.pdf",
            "jd_id": "jd1",
            "exact_matching": valid_exact,
        },
        job_description=jd_skills_obj,
    )
    assert cand_valid.status == "complete"
    assert cand_valid.final_score == 100.0
    assert cand_valid.breakdown["required_skills"].status == "complete"
    assert cand_valid.breakdown["required_skills"].score == 100.0

    # 2. Valid retrieval with zero matches (LLM assessed, 0 matched): score 0, complete
    zero_exact = ExactMatchingResult(
        total_required_skills=2,
        matched_required_skills=0,
        unmatched_required_skills=2,
        status="completed",
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=False, resume_skill=None),
            ExactSkillMatchItem(required_skill="FastAPI", matched=False, resume_skill=None),
        ]
    )
    cand_zero = engine.score_candidate(
        match_result={
            "upload_id": "b1",
            "filename": "cand_zero.pdf",
            "jd_id": "jd1",
            "exact_matching": zero_exact,
        },
        job_description=jd_skills_obj,
    )
    assert cand_zero.status == "complete"
    assert cand_zero.final_score == 0.0
    assert cand_zero.breakdown["required_skills"].status == "complete"
    assert cand_zero.breakdown["required_skills"].score == 0.0

    # 3. Empty resume skills: valid empty evidence, score 0, complete
    empty_skills_exact = {
        "total_required_skills": 2,
        "matched_required_skills": 0,
        "unmatched_required_skills": 2,
        "status": "completed",
        "matches": [
            {"required_skill": "Python", "matched": False, "resume_skill": None},
            {"required_skill": "FastAPI", "matched": False, "resume_skill": None},
        ]
    }
    cand_empty_skills = engine.score_candidate(
        match_result={
            "upload_id": "b1",
            "filename": "cand_empty_skills.pdf",
            "jd_id": "jd1",
            "exact_matching": empty_skills_exact,
        },
        job_description=jd_skills_obj,
    )
    assert cand_empty_skills.status == "complete"
    assert cand_empty_skills.final_score == 0.0
    assert cand_empty_skills.breakdown["required_skills"].status == "complete"
    assert cand_empty_skills.breakdown["required_skills"].score == 0.0

    # 4. Ollama timeout: status=failed -> unavailable -> candidate incomplete, final_score=None
    timeout_exact = ExactMatchingResult(
        total_required_skills=2,
        matched_required_skills=0,
        unmatched_required_skills=2,
        status="failed",
        error="LLM skill matching failed: TimeoutError('Ollama read timeout after 300s')",
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=False, resume_skill=None),
            ExactSkillMatchItem(required_skill="FastAPI", matched=False, resume_skill=None),
        ]
    )
    cand_timeout = engine.score_candidate(
        match_result={
            "upload_id": "b1",
            "filename": "cand_timeout.pdf",
            "jd_id": "jd1",
            "exact_matching": timeout_exact,
        },
        job_description=jd_skills_obj,
    )
    assert cand_timeout.status == "incomplete"
    assert cand_timeout.final_score is None
    assert cand_timeout.breakdown["required_skills"].status == "unavailable"
    assert cand_timeout.breakdown["required_skills"].score is None
    assert any("required_skills" in err for err in cand_timeout.errors)

    # 5. Connection failure: status=failed -> unavailable -> candidate incomplete, final_score=None
    conn_fail_exact = {
        "total_required_skills": 2,
        "matched_required_skills": 0,
        "unmatched_required_skills": 2,
        "status": "failed",
        "error": "LLM skill matching failed: ConnectionError('Failed to connect to Ollama')",
        "matches": []
    }
    cand_conn = engine.score_candidate(
        match_result={
            "upload_id": "b1",
            "filename": "cand_conn.pdf",
            "jd_id": "jd1",
            "exact_matching": conn_fail_exact,
        },
        job_description=jd_skills_obj,
    )
    assert cand_conn.status == "incomplete"
    assert cand_conn.final_score is None
    assert cand_conn.breakdown["required_skills"].status == "unavailable"

    # 6. Invalid JSON / Malformed model output: status=failed -> unavailable
    malformed_exact = {
        "total_required_skills": 2,
        "matched_required_skills": 0,
        "unmatched_required_skills": 2,
        "status": "failed",
        "error": "LLM skill matching failed: ValueError('Invalid JSON returned by LLM')",
        "matches": []
    }
    cand_malformed = engine.score_candidate(
        match_result={
            "upload_id": "b1",
            "filename": "cand_malformed.pdf",
            "jd_id": "jd1",
            "exact_matching": malformed_exact,
        },
        job_description=jd_skills_obj,
    )
    assert cand_malformed.status == "incomplete"
    assert cand_malformed.final_score is None

    # 7. Multi-candidate ranking separates failed candidate to unranked (never fabricated zero)
    ranked_list, unranked_list = engine.rank_candidates([cand_valid, cand_zero, cand_timeout])
    assert len(ranked_list) == 2
    assert ranked_list[0].filename == "cand1.pdf" and ranked_list[0].rank == 1 and ranked_list[0].final_score == 100.0
    assert ranked_list[1].filename == "cand_zero.pdf" and ranked_list[1].rank == 2 and ranked_list[1].final_score == 0.0
    assert len(unranked_list) == 1
    assert unranked_list[0].filename == "cand_timeout.pdf" and unranked_list[0].rank is None and unranked_list[0].final_score is None
    print_status("Test 46: Finding 1 - Required Skills failure propagation & valid zero distinction verified", True)

    # ==============================================================================
    # Test 47: Finding 2 — Experience decision index alignment & non-leakage
    # ==============================================================================
    jd_multi_domain = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(preferred_domains=["Computer Vision", "Fintech"])
        ]
    )

    exp_cv = CandidateExperienceItem(
        experience_index=10,
        role="CV Scientist",
        company="VisionAI",
        relevant=True,
        decision="RELEVANT",
        matched_domains=["Computer Vision"],
    )

    exp_quant = CandidateExperienceItem(
        experience_index=25,
        role="Quantitative Trader",
        company="HedgeFund",
        relevant=True,
        decision="RELEVANT",
        matched_domains=["Fintech"],
    )

    # Subcase 1: Sequential / normal ordering
    exp_matching_norm = ExperienceMatchingResult(
        experiences=[exp_cv, exp_quant]
    )
    score_47a, stat_47a, tot_47a, qual_47a, evid_47a, _ = engine.calculate_experience_relevance_score(
        exp_matching_norm,
        jd_multi_domain,
    )
    assert stat_47a == "complete" and qual_47a == 2 and score_47a == 100.0
    assert evid_47a[0]["criterion"] == "Computer Vision" and evid_47a[0]["supporting_role"] == "CV Scientist"
    assert evid_47a[1]["criterion"] == "Fintech" and evid_47a[1]["supporting_role"] == "Quantitative Trader"

    # Subcase 2: Reordered experiences (exp_quant first, exp_cv second)
    # Auxiliary decisions indexed strictly by experience_index 10 and 25
    aux_relevance_decisions = [
        {"experience_index": 10, "decision": "RELEVANT", "matched_domains": ["Computer Vision"], "reason": "CV role"},
        {"experience_index": 25, "decision": "RELEVANT", "matched_domains": ["Fintech"], "reason": "Quant role"},
    ]
    exp_matching_reordered = ExperienceMatchingResult(
        experiences=[exp_quant, exp_cv]  # Reordered: index 25 first, index 10 second
    )
    score_47b, stat_47b, tot_47b, qual_47b, evid_47b, _ = engine.calculate_experience_relevance_score(
        exp_matching_reordered,
        jd_multi_domain,
        relevance_decisions=aux_relevance_decisions,
    )
    # Verification: Lookup by experience_index ensures no domain evidence leaks across experiences!
    assert stat_47b == "complete" and qual_47b == 2 and score_47b == 100.0
    assert evid_47b[0]["criterion"] == "Computer Vision" and evid_47b[0]["supporting_role"] == "CV Scientist"
    assert evid_47b[1]["criterion"] == "Fintech" and evid_47b[1]["supporting_role"] == "Quantitative Trader"

    # Subcase 3: Verify non-matching domain cannot leak or qualify
    exp_healthcare = CandidateExperienceItem(
        experience_index=99,
        role="Bioinformatics Specialist",
        company="GenomicsLab",
        relevant=True,
        decision="RELEVANT",
        matched_domains=["Healthcare"],
    )
    exp_matching_single_unmatched = ExperienceMatchingResult(
        experiences=[exp_healthcare]
    )
    score_47c, stat_47c, tot_47c, qual_47c, evid_47c, _ = engine.calculate_experience_relevance_score(
        exp_matching_single_unmatched,
        jd_multi_domain,
    )
    assert stat_47c == "complete" and qual_47c == 0 and score_47c == 0.0
    assert evid_47c[0]["qualifies"] is False and "does not explicitly match" in evid_47c[0]["reason"]
    assert evid_47c[1]["qualifies"] is False and "does not explicitly match" in evid_47c[1]["reason"]

    # Subcase 4: Auxiliary decision with non-sequential index matching dict experience
    dict_exp_matching = {
        "experiences": [
            {"experience_index": 42, "role": "Computer Vision Eng", "company": "RobotCorp"}
        ]
    }
    dict_aux = [
        {"experience_index": 42, "decision": "RELEVANT", "matched_domains": ["Computer Vision"], "reason": "Robotics CV"}
    ]
    score_47d, stat_47d, tot_47d, qual_47d, evid_47d, _ = engine.calculate_experience_relevance_score(
        dict_exp_matching,
        jd_multi_domain,
        relevance_decisions=dict_aux,
    )
    assert stat_47d == "complete" and qual_47d == 1 and score_47d == 50.0
    assert evid_47d[0]["criterion"] == "Computer Vision" and evid_47d[0]["qualifies"] is True
    assert evid_47d[1]["criterion"] == "Fintech" and evid_47d[1]["qualifies"] is False
    print_status("Test 47: Finding 2 - Experience decision index alignment & non-leakage verified", True)

    print("\n" + "=" * 80)
    print("ALL UNIT & AUDIT TESTS (Cases 1 through 47) PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_unit_tests()


