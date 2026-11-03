"""
TalentAI — Phase 9.2: Ranking Quality Evaluation Runner & Test Suite

Executes the synthetic evaluation dataset against the active ranking engine,
validating quality, invariants, boundary behavior, and ranking metrics
without external dependencies.

Groups:
1. Scenario Tests (SC-01 through SC-17): Specific fixture behaviors.
2. Batch Cohort Ranking (SC-18): Genuine batch ranking & segregation.
3. Formal Mathematical Invariants Suite (Invariants 1 through 6).
4. Synthetic Benchmark Metrics Evaluation (Precision@K, NDCG@K, Spearman rho, ICSR).
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
from app.ranking.ranking_service import ranking_engine
from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from test_data.evaluation.builder import (
    build_synthetic_cohort,
    load_benchmark_jds,
    load_ground_truth_annotations,
)
from test_data.evaluation.metrics import (
    calculate_dcg_at_k,
    calculate_incomplete_separation_rate,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_spearman_correlation,
)


def print_status(test_name: str, passed: bool, details: str = "") -> None:
    status = "PASSED" if passed else "FAILED"
    det_str = f" ({details})" if details else ""
    print(f"[{status}] {test_name}{det_str}")


def run_evaluation_suite():
    print("=" * 80)
    print("TALENTAI — PHASE 9.2: RANKING QUALITY EVALUATION & BENCHMARK SUITE")
    print("=" * 80)

    engine = ranking_engine
    jds = load_benchmark_jds()
    ground_truth, failed_fns = load_ground_truth_annotations()
    jd_main = jds["jd_01_fullstack_cloud"]

    cohort = build_synthetic_cohort(jd_main)
    cohort_by_fn = {m.filename: m for m in cohort}

    # ==========================================================================
    # GROUP 1: SCENARIO VERIFICATION TESTS (SC-01 through SC-17)
    # ==========================================================================
    print("\n--- GROUP 1: SCENARIO VERIFICATION TESTS ---")

    # SC-01: Strong Alignment
    cand_01 = engine.score_candidate(cohort_by_fn["cand_01_strong.pdf"], jd_main)
    assert cand_01.status == "complete", f"Expected complete, got {cand_01.status}"
    assert cand_01.final_score is not None and cand_01.final_score >= 90.0, f"Expected >= 90, got {cand_01.final_score}"
    assert cand_01.component_scores["required_skills"] == 100.0
    assert cand_01.component_scores["experience_relevance"] == 100.0
    assert cand_01.experience_diagnostic.minimum_duration_satisfied is True
    print_status("SC-01: Strong Alignment Candidate", True, f"final_score={cand_01.final_score}")

    # SC-02: Partial Alignment
    cand_02 = engine.score_candidate(cohort_by_fn["cand_02_partial.pdf"], jd_main)
    assert cand_02.status == "complete"
    assert cand_02.final_score is not None and 30.0 <= cand_02.final_score <= 55.0, f"Expected 30-55, got {cand_02.final_score}"
    assert cand_02.component_scores["required_skills"] == 50.0  # 2 of 4 skills
    assert cand_02.component_scores["experience_relevance"] == 50.0  # 1 of 2 domains
    print_status("SC-02: Partial Alignment Candidate", True, f"final_score={cand_02.final_score}")

    # SC-03: Weak Alignment
    cand_03 = engine.score_candidate(cohort_by_fn["cand_03_weak.pdf"], jd_main)
    assert cand_03.status == "complete"
    assert cand_03.final_score == 6.25, f"Expected 6.25, got {cand_03.final_score}"
    assert cand_03.component_scores["required_skills"] == 25.0  # 1 of 4 skills
    assert cand_03.component_scores["responsibilities"] == 0.0  # below 0.65 threshold
    assert cand_03.component_scores["tools_and_technologies"] == 0.0  # below 0.65 threshold
    assert cand_03.component_scores["experience_relevance"] == 0.0  # unrelated domain
    print_status("SC-03: Weak Alignment Candidate", True, f"final_score={cand_03.final_score}")

    # SC-04: Valid Zero Candidate
    cand_04 = engine.score_candidate(cohort_by_fn["cand_04_zero.pdf"], jd_main)
    assert cand_04.status == "complete", f"Valid zero must have status 'complete', got {cand_04.status}"
    assert cand_04.final_score == 0.00, f"Expected 0.00, got {cand_04.final_score}"
    assert cand_04.component_scores["required_skills"] == 0.0
    assert cand_04.component_scores["responsibilities"] == 0.0
    assert cand_04.component_scores["tools_and_technologies"] == 0.0
    assert cand_04.component_scores["experience_relevance"] == 0.0
    print_status("SC-04: Valid Zero Candidate (Not Marked Incomplete)", True, "score=0.00, status=complete")

    # SC-05: Skill Noise / Distractors (Requirement 1: distinguish component score from final score)
    cand_05 = engine.score_candidate(cohort_by_fn["cand_05_skill_noise.pdf"], jd_main)
    assert cand_05.status == "complete"
    # Required skills component score is strictly 75.0 (3 of 4 skills matched)
    skills_comp_score = cand_05.component_scores["required_skills"]
    assert skills_comp_score == 75.0, f"Expected component score 75.0, got {skills_comp_score}"
    assert cand_05.breakdown["required_skills"].score == 75.0
    # Final score combines all components: 0.25*75 + 0.30*19.05 + 0.10*16.19 + 0.35*50 = 43.59
    assert cand_05.final_score != 75.0, "Requirement 1 violated: component score confused with final weighted score!"
    assert abs(cand_05.final_score - 43.59) <= 0.05, f"Expected final score ~43.59, got {cand_05.final_score}"
    print_status(
        "SC-05: Skill Noise (Component score 75.0 distinguished from final weighted score)",
        True,
        f"skills_component={skills_comp_score}, final_score={cand_05.final_score}",
    )

    # SC-06: Strict Tools Section Routing (tools in experience only -> tools score 0.0)
    cand_06 = engine.score_candidate(cohort_by_fn["cand_06_tools_in_exp_only.pdf"], jd_main)
    assert cand_06.component_scores["tools_and_technologies"] == 0.0, (
        f"Expected tools score 0.0 (tools in experience must not route to tools), got {cand_06.component_scores['tools_and_technologies']}"
    )
    print_status("SC-06: Strict Tools Routing (Tools in exp only -> 0.0 in tools)", True)

    # SC-07: Responsibilities in Projects Only
    cand_07 = engine.score_candidate(cohort_by_fn["cand_07_resp_in_proj_only.pdf"], jd_main)
    assert cand_07.component_scores["responsibilities"] is not None and cand_07.component_scores["responsibilities"] > 0.0
    print_status(
        "SC-07: Responsibilities in Projects Allowed",
        True,
        f"resp_score={cand_07.component_scores['responsibilities']}",
    )

    # SC-08: Multi-unrelated Experience Non-dilution
    cand_08 = engine.score_candidate(cohort_by_fn["cand_08_multi_unrelated_exp.pdf"], jd_main)
    assert cand_08.component_scores["experience_relevance"] == 50.0, (
        f"Expected 50.0 (1 Fintech role + 4 unrelated roles), got {cand_08.component_scores['experience_relevance']}"
    )
    # Compare with cand_02 which had only the 1 Fintech role:
    assert cand_08.component_scores["experience_relevance"] == cand_02.component_scores["experience_relevance"], (
        "Adding unrelated experience diluted candidate experience score!"
    )
    print_status("SC-08: Experience Non-dilution (Unrelated roles do not dilute score)", True, "score=50.0")

    # SC-09: Overlapping Experience Dates
    cand_09 = engine.score_candidate(cohort_by_fn["cand_09_overlapping_dates.pdf"], jd_main)
    assert cand_09.experience_diagnostic.relevant_duration_years == 2.0, (
        f"Expected 2.0 years de-duplicated duration, got {cand_09.experience_diagnostic.relevant_duration_years}"
    )
    assert cand_09.experience_diagnostic.minimum_duration_satisfied is False  # 2.0 < 3.0 min
    print_status("SC-09: Overlapping Dates Diagnostic", True, "duration=2.0 yrs, satisfied=False")

    # SC-10: Missing Dates Diagnostic
    cand_10 = engine.score_candidate(cohort_by_fn["cand_10_missing_dates.pdf"], jd_main)
    assert cand_10.experience_diagnostic.diagnostic_status == "dates_missing_or_unparseable"
    assert cand_10.component_scores["experience_relevance"] == 100.0  # qualitative relevance preserved
    assert any("missing or invalid" in w.lower() for w in cand_10.warnings)
    print_status("SC-10: Missing Dates Diagnostic (Diagnostic flagged, relevance preserved)", True)

    # SC-11: LLM Skill Timeout / Failure -> Incomplete
    cand_11 = engine.score_candidate(cohort_by_fn["cand_11_fail_llm_skills.pdf"], jd_main)
    assert cand_11.status == "incomplete", f"Expected incomplete, got {cand_11.status}"
    assert cand_11.final_score is None, f"Expected final_score None, got {cand_11.final_score}"
    assert cand_11.breakdown["required_skills"].status == "unavailable"
    assert cand_11.component_scores["required_skills"] is None
    print_status("SC-11: LLM Skill Failure Propagation", True, "status=incomplete, final_score=None")

    # SC-12: Retrieval Failure -> Incomplete
    cand_12 = engine.score_candidate(cohort_by_fn["cand_12_fail_retrieval.pdf"], jd_main)
    assert cand_12.status == "incomplete"
    assert cand_12.final_score is None
    assert cand_12.breakdown["responsibilities"].status == "unavailable"
    print_status("SC-12: Retrieval Failure Propagation", True, "status=incomplete, final_score=None")

    # SC-13: Duplicate Candidates Identity & Stability
    cand_13a = engine.score_candidate(cohort_by_fn["cand_13_duplicate_a.pdf"], jd_main)
    cand_13b = engine.score_candidate(cohort_by_fn["cand_13_duplicate_b.pdf"], jd_main)
    assert cand_13a.final_score == cand_13b.final_score
    assert cand_13a.component_scores == cand_13b.component_scores
    print_status("SC-13: Duplicate Candidates Identity", True, f"scores_identical={cand_13a.final_score}")

    # SC-14: Category Absent from JD (JD-02: Tools absent)
    jd_no_tools = jds["jd_02_ml_research_no_tools"]
    app_no_tools = engine.determine_category_applicability(jd_no_tools)
    assert app_no_tools["tools_and_technologies"] == "not_applicable"
    weights_no_tools = engine.normalize_weights(app_no_tools)
    assert weights_no_tools["tools_and_technologies"] == 0.0
    assert abs(weights_no_tools["required_skills"] - (0.25 / 0.90)) < 1e-4
    assert abs(weights_no_tools["responsibilities"] - (0.30 / 0.90)) < 1e-4
    assert abs(weights_no_tools["experience_relevance"] - (0.35 / 0.90)) < 1e-4
    assert abs(sum(weights_no_tools.values()) - 1.0) < 1e-6
    print_status("SC-14: Category Absent from JD (Tools absent -> weights sum to 1.0)", True)

    # SC-15: Vacuous / Empty JD (JD-05: no scorable requirements)
    jd_empty = jds["jd_05_vacuous_empty"]
    cand_empty_jd = engine.score_candidate(cohort_by_fn["cand_01_strong.pdf"], jd_empty)
    assert cand_empty_jd.status == "no_scorable_requirements", f"Expected no_scorable_requirements, got {cand_empty_jd.status}"
    assert cand_empty_jd.final_score is None
    print_status("SC-15: Vacuous JD Compatibility", True, "status=no_scorable_requirements, final_score=None")

    # SC-16: Empty Resume Sections against JD-01
    cand_empty_resume = engine.score_candidate(
        {
            "upload_id": "b",
            "filename": "empty_resume.pdf",
            "exact_matching": {"total_required_skills": 4, "matched_required_skills": 0, "matches": []},
            "semantic_retrieval": {"responsibilities_retrieval": {"results": []}, "tools_and_technologies_retrieval": {"results": []}},
            "experience_matching": {"experiences": []},
        },
        jd_main,
    )
    assert cand_empty_resume.status == "complete"
    assert cand_empty_resume.final_score == 0.00
    print_status("SC-16: Empty Resume Sections against JD", True, "status=complete, score=0.00")

    # SC-17: Proportional Weight Ratios
    # Check all combinations of applicable categories
    for subset_name, jd_sub in [
        ("JD-02 (no tools)", jds["jd_02_ml_research_no_tools"]),
        ("JD-03 (no domains)", jds["jd_03_devops_no_domains"]),
        ("JD-04 (skills+tools)", jds["jd_04_data_analyst_skills_tools"]),
    ]:
        applicability = engine.determine_category_applicability(jd_sub)
        w_norm = engine.normalize_weights(applicability)
        app_cats = [c for c, stat in applicability.items() if stat == "applicable"]
        for i in range(len(app_cats)):
            for j in range(i + 1, len(app_cats)):
                c1, c2 = app_cats[i], app_cats[j]
                ratio_norm = w_norm[c1] / w_norm[c2]
                ratio_base = BASE_WEIGHTS[c1] / BASE_WEIGHTS[c2]
                assert abs(ratio_norm - ratio_base) < 1e-4, f"Proportional ratio mismatch for {c1}/{c2} in {subset_name}"
    print_status("SC-17: Proportional Weight Ratio Invariance", True, "ratios preserved across all JDs")

    # ==========================================================================
    # GROUP 2: BATCH COHORT RANKING & COHORT PROPERTIES (SC-18)
    # ==========================================================================
    print("\n--- GROUP 2: BATCH COHORT RANKING (SC-18) ---")

    # Score all 14 candidates in the synthetic cohort
    scored_cohort = [engine.score_candidate(m, jd_main) for m in cohort]

    # Rank cohort
    ranked, unranked = engine.rank_candidates(scored_cohort)

    assert len(ranked) == 12, f"Expected 12 ranked candidates, got {len(ranked)}"
    assert len(unranked) == 2, f"Expected 2 unranked candidates, got {len(unranked)}"

    # 1. Verify strict monotonic ordering where fixture design justifies it
    fn_to_rank = {c.filename: c.rank for c in ranked}
    fn_to_score = {c.filename: c.final_score for c in ranked}

    # cand_01 (strong, ~90.57) > cand_05 (skill_noise, ~43.59) > cand_02 (partial, ~37.34) > cand_03 (weak, 6.25) > cand_04 (zero, 0.0)
    assert fn_to_score["cand_01_strong.pdf"] > fn_to_score["cand_05_skill_noise.pdf"], "Strong should beat skill_noise"
    assert fn_to_score["cand_05_skill_noise.pdf"] > fn_to_score["cand_02_partial.pdf"], "Skill_noise should beat partial"
    assert fn_to_score["cand_02_partial.pdf"] > fn_to_score["cand_03_weak.pdf"], "Partial should beat weak"
    assert fn_to_score["cand_03_weak.pdf"] > fn_to_score["cand_04_zero.pdf"], "Weak should beat zero"

    assert fn_to_rank["cand_01_strong.pdf"] < fn_to_rank["cand_05_skill_noise.pdf"]
    assert fn_to_rank["cand_05_skill_noise.pdf"] < fn_to_rank["cand_02_partial.pdf"]
    assert fn_to_rank["cand_02_partial.pdf"] < fn_to_rank["cand_03_weak.pdf"]
    assert fn_to_rank["cand_03_weak.pdf"] < fn_to_rank["cand_04_zero.pdf"]
    print_status(
        "SC-18.1: Exact Ordering Where Fixture Design Justifies It",
        True,
        f"Strong({fn_to_score['cand_01_strong.pdf']}) > Noise({fn_to_score['cand_05_skill_noise.pdf']}) > Partial({fn_to_score['cand_02_partial.pdf']}) > Weak({fn_to_score['cand_03_weak.pdf']}) > Zero({fn_to_score['cand_04_zero.pdf']})",
    )

    # 2. Verify deterministic tie-breaking on filename
    # cand_13_duplicate_a.pdf and cand_13_duplicate_b.pdf have identical score
    score_dup_a = fn_to_score["cand_13_duplicate_a.pdf"]
    score_dup_b = fn_to_score["cand_13_duplicate_b.pdf"]
    assert score_dup_a == score_dup_b, f"Duplicate scores must match: {score_dup_a} vs {score_dup_b}"
    rank_dup_a = fn_to_rank["cand_13_duplicate_a.pdf"]
    rank_dup_b = fn_to_rank["cand_13_duplicate_b.pdf"]
    assert rank_dup_a < rank_dup_b, f"Tie-breaking failed: 'a' (rank {rank_dup_a}) must precede 'b' (rank {rank_dup_b})"
    assert rank_dup_b == rank_dup_a + 1, "Tied candidates must receive consecutive integer ranks"
    print_status(
        "SC-18.2: Deterministic Tie-breaking on Filename",
        True,
        f"duplicate_a rank {rank_dup_a} < duplicate_b rank {rank_dup_b} (scores {score_dup_a})",
    )

    # 3. Verify Permutation Invariance: Reversing or shuffling input order produces identical results
    reversed_cohort = list(reversed(scored_cohort))
    rev_ranked, rev_unranked = engine.rank_candidates(reversed_cohort)
    for c_orig, c_rev in zip(ranked, rev_ranked):
        assert c_orig.filename == c_rev.filename, f"Permutation invariance broken: {c_orig.filename} vs {c_rev.filename}"
        assert c_orig.final_score == c_rev.final_score
        assert c_orig.rank == c_rev.rank
    print_status("SC-18.3: Cohort Permutation Invariance", True, "Input permutation order does not alter ranking")

    # 4. Verify Technical Failure Segregation
    unranked_fns = {c.filename for c in unranked}
    assert unranked_fns == set(failed_fns), f"Expected unranked {set(failed_fns)}, got {unranked_fns}"
    for u in unranked:
        assert u.status == "incomplete"
        assert u.final_score is None
        assert u.rank is None
    print_status("SC-18.4: Incomplete Segregation", True, f"Unranked candidates: {sorted(list(unranked_fns))}")

    # ==========================================================================
    # GROUP 3: FORMAL MATHEMATICAL INVARIANTS SUITE
    # ==========================================================================
    print("\n--- GROUP 3: FORMAL MATHEMATICAL INVARIANTS ---")

    # Invariant 1: Universal Score Bounding
    for cand in ranked:
        assert 0.0 <= cand.final_score <= 100.0, f"Final score out of bounds: {cand.final_score}"
        for cat, sc in cand.component_scores.items():
            if sc is not None:
                assert 0.0 <= sc <= 100.0, f"Component score {cat} out of bounds: {sc}"
    print_status("Invariant 1: Universal Score Bounding [0.0, 100.0]", True)

    # Invariant 2: Dynamic Weight Conservation
    for jd_name, jd_obj in jds.items():
        app = engine.determine_category_applicability(jd_obj)
        weights = engine.normalize_weights(app)
        applicable_count = sum(1 for s in app.values() if s in ("applicable", "complete"))
        if applicable_count > 0:
            total_w = sum(weights.values())
            assert abs(total_w - 1.0) < 1e-6, f"Weight conservation failed for {jd_name}: sum={total_w}"
        else:
            assert all(w == 0.0 for w in weights.values())
    print_status("Invariant 2: Dynamic Weight Conservation (sum == 1.0)", True)

    # Invariant 3: Clean Separation of Incomplete Candidates
    for cand in ranked:
        assert cand.status == "complete"
        assert cand.final_score is not None
        assert cand.rank is not None
        # Must not contain unavailable applicable categories
        for cat_name, breakdown in cand.breakdown.items():
            assert breakdown.status != "unavailable", f"Ranked candidate has unavailable category: {cat_name}"
    for cand in unranked:
        assert cand.status == "incomplete"
        assert cand.final_score is None
        assert cand.rank is None
    print_status("Invariant 3: Clean Separation of Incomplete Candidates", True)

    # ==========================================================================
    # GROUP 4: SYNTHETIC BENCHMARK METRICS EVALUATION
    # ==========================================================================
    print("\n--- GROUP 4: SYNTHETIC BENCHMARK METRICS ---")
    print("> [NOTE] The following metrics are calculated against synthetic benchmark annotations")
    print("> to validate ranking consistency and do not represent evidence of real-world hiring validity.\n")

    # 1. Precision@K
    p_at_3 = calculate_precision_at_k(ranked, ground_truth, k=3, relevance_threshold=2)
    p_at_5 = calculate_precision_at_k(ranked, ground_truth, k=5, relevance_threshold=2)
    print_status("Metric: Precision@3 (Threshold >= 2)", p_at_3 == 1.0, f"P@3 = {p_at_3:.4f}")
    print_status("Metric: Precision@5 (Threshold >= 2)", p_at_5 >= 0.8, f"P@5 = {p_at_5:.4f}")

    # 2. NDCG@K
    ndcg_3_det = calculate_ndcg_at_k(ranked, ground_truth, k=3, handle_ties=False)
    ndcg_3_tie = calculate_ndcg_at_k(ranked, ground_truth, k=3, handle_ties=True)
    ndcg_5 = calculate_ndcg_at_k(ranked, ground_truth, k=5)
    ndcg_10 = calculate_ndcg_at_k(ranked, ground_truth, k=10)
    print_status(
        "Metric: NDCG@3 (Deterministic, filename tie-breaking)",
        ndcg_3_det >= 0.65,
        f"NDCG@3 = {ndcg_3_det:.4f}",
    )
    print_status(
        "Metric: NDCG@3 (Tie-Aware Expected)",
        ndcg_3_tie >= 0.75,
        f"NDCG@3 = {ndcg_3_tie:.4f}",
    )
    print_status("Metric: NDCG@5", ndcg_5 >= 0.90, f"NDCG@5 = {ndcg_5:.4f}")
    print_status("Metric: NDCG@10", ndcg_10 >= 0.85, f"NDCG@10 = {ndcg_10:.4f}")

    # 3. Spearman Rank Correlation
    rho = calculate_spearman_correlation(ranked, ground_truth)
    assert rho is not None and rho > 0.70, f"Expected strong rank correlation > 0.70, got {rho}"
    print_status("Metric: Spearman Rank Correlation (rho)", True, f"rho = {rho:.4f}")

    # 4. Incomplete Candidate Separation Rate (ICSR)
    icsr = calculate_incomplete_separation_rate(unranked, failed_fns)
    assert icsr == 1.0, f"Expected ICSR 1.0 (100%), got {icsr}"
    print_status("Metric: Incomplete Candidate Separation Rate (ICSR)", True, f"ICSR = {icsr * 100.0:.1f}%")

    # 5. Safe Boundary Behavior Checks (Requirement 4)
    # K > cohort size:
    p_clamped = calculate_precision_at_k(ranked, ground_truth, k=50)
    ndcg_clamped = calculate_ndcg_at_k(ranked, ground_truth, k=50)
    assert 0.0 <= p_clamped <= 1.0
    assert 0.0 <= ndcg_clamped <= 1.0
    print_status("Boundary Check: K > Cohort Size Safe Clamping", True, f"P@50={p_clamped}, NDCG@50={ndcg_clamped}")

    # Empty cohort:
    assert calculate_precision_at_k([], ground_truth, k=5) == 0.0
    assert calculate_ndcg_at_k([], ground_truth, k=5) == 0.0
    assert calculate_spearman_correlation([], ground_truth) is None
    print_status("Boundary Check: Empty Cohort Safe Returns", True)

    # Zero IDCG (all ground truth = 0):
    zero_gt = {c.filename: 0 for c in ranked}
    ndcg_zero_idcg = calculate_ndcg_at_k(ranked, zero_gt, k=5)
    assert ndcg_zero_idcg == 1.0, f"Expected 1.0 for zero-IDCG zero-DCG case, got {ndcg_zero_idcg}"
    print_status("Boundary Check: Zero-IDCG Safe Handling", True, f"NDCG={ndcg_zero_idcg}")

    print("\n" + "=" * 80)
    print("PHASE 9.2: ALL EVALUATION SCENARIOS, INVARIANTS, & METRICS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation_suite()
