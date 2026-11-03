"""
TalentAI — Stage 5E.2: Standalone Isolated Synthetic Pilot Runner

This module implements the isolated, offline test suite for comparing legacy
and evidence-based experience ranking engines against the Stage 5E.2.1 pilot
specification.

Construction Mode:
This runner is constructed for future separately authorized execution.
It relies strictly on synthetic in-memory fixtures and avoids all database,
filesystem, API, and batch dependencies.

Test Groups:
- Group A: Legacy and Evidence Engine Comparison (Invariance & Flags)
- Group B: Experience Scoring Behavior & Edge Cases
- Group C: Approved Time-Sliced Weighted Duration Pooling
- Group D: Pilot Metric Preparation Utilities (Precision, Recall, NDCG, Ties)
- Group E: Explanation, Traceability, and Provenance Verification
"""

import copy
from datetime import date
import math
from pathlib import Path
import sys
import unittest

# Ensure backend and pilot directories are in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
PILOT_DIR = Path(__file__).resolve().parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PILOT_DIR) not in sys.path:
    sys.path.insert(0, str(PILOT_DIR))

from app.ranking.ranking_config import BASE_WEIGHTS, USE_EVIDENCE_BASED_EXPERIENCE
from app.ranking.ranking_service import RankingEngine
from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.services.experience_matching_service import experience_matching_service
from fixtures import (
    JD_PILOT_01,
    JD_PILOT_02,
    JD_PILOT_03,
    JOB_DESCRIPTIONS,
    SYNTHETIC_CANDIDATE_FIXTURES,
    get_candidate_match_result,
    get_candidate_meta,
    get_jd_cohort_candidate_ids,
)
from metrics import (
    calculate_cohen_kappa,
    calculate_dcg_at_k,
    calculate_idcg_at_k,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_spearman_rho,
    calculate_tie_counts_and_rates,
    human_grade_to_binary,
)


class TestStage5E2PilotRunner(unittest.TestCase):
    """
    Standalone Pilot Test Runner evaluating legacy vs evidence-based ranking engines.
    """

    def setUp(self):
        """Instantiate independent engines using explicit constructor arguments."""
        self.engine_legacy = RankingEngine(use_evidence_based_experience=False)
        self.engine_evidence = RankingEngine(use_evidence_based_experience=True)

    # ==========================================================================
    # GROUP A: LEGACY AND EVIDENCE ENGINE COMPARISON
    # ==========================================================================

    def test_group_a_identical_inputs_and_components_a_b_c_invariance(self):
        """
        Verify that supplying identical inputs to legacy and evidence engines
        produces 100% numerically identical scores for Components A, B, and C.
        """
        cand_id = "CAND-01"
        match_result = get_candidate_match_result(cand_id)
        jd = JD_PILOT_01

        # Deep copy ensures zero mutation between calls
        input_legacy = copy.deepcopy(match_result)
        input_evidence = copy.deepcopy(match_result)

        res_legacy = self.engine_legacy.score_candidate(input_legacy, jd)
        res_evidence = self.engine_evidence.score_candidate(input_evidence, jd)

        # Component A: Required Skills (25%)
        self.assertEqual(
            res_legacy.breakdown["required_skills"].score,
            res_evidence.breakdown["required_skills"].score,
            "Component A score must be strictly identical between engines.",
        )
        self.assertEqual(
            res_legacy.breakdown["required_skills"].normalized_weight,
            res_evidence.breakdown["required_skills"].normalized_weight,
            "Component A weight must be strictly identical between engines.",
        )

        # Component B: Responsibilities (30%)
        self.assertEqual(
            res_legacy.breakdown["responsibilities"].score,
            res_evidence.breakdown["responsibilities"].score,
            "Component B score must be strictly identical between engines.",
        )
        self.assertEqual(
            res_legacy.breakdown["responsibilities"].normalized_weight,
            res_evidence.breakdown["responsibilities"].normalized_weight,
            "Component B weight must be strictly identical between engines.",
        )

        # Component C: Tools & Technologies (10%)
        self.assertEqual(
            res_legacy.breakdown["tools_and_technologies"].score,
            res_evidence.breakdown["tools_and_technologies"].score,
            "Component C score must be strictly identical between engines.",
        )
        self.assertEqual(
            res_legacy.breakdown["tools_and_technologies"].normalized_weight,
            res_evidence.breakdown["tools_and_technologies"].normalized_weight,
            "Component C weight must be strictly identical between engines.",
        )

    def test_group_a_score_delta_attributable_only_to_component_d(self):
        """
        Verify that the final score difference between legacy and evidence engines
        is strictly attributable to Component D: Delta_final = 0.35 * (E_ev - E_leg).
        """
        cand_id = "CAND-02"  # Proportional damping candidate
        match_result = get_candidate_match_result(cand_id)
        jd = JD_PILOT_01

        res_legacy = self.engine_legacy.score_candidate(copy.deepcopy(match_result), jd)
        res_evidence = self.engine_evidence.score_candidate(copy.deepcopy(match_result), jd)

        score_leg = res_legacy.final_score
        score_ev = res_evidence.final_score
        exp_leg = res_legacy.breakdown["experience_relevance"].score
        exp_ev = res_evidence.breakdown["experience_relevance"].score

        delta_final = score_ev - score_leg
        expected_delta = 0.35 * (exp_ev - exp_leg)
        expected_delta_rounded = round(expected_delta, 2)

        # Production final_score is rounded to 2 decimal places (ranking_service.py:1456).
        # We assert the approved relationship holds within 2-decimal display precision:
        self.assertAlmostEqual(
            delta_final,
            expected_delta_rounded,
            places=2,
            msg=f"Final score delta ({delta_final:.2f}) must equal 0.35 * exp delta rounded ({expected_delta_rounded:.2f}).",
        )

    def test_group_a_global_feature_flag_is_not_changed(self):
        """
        Verify that constructor-level engine instantiation does not alter
        the global USE_EVIDENCE_BASED_EXPERIENCE feature flag.
        """
        self.assertFalse(
            USE_EVIDENCE_BASED_EXPERIENCE,
            "Global feature flag USE_EVIDENCE_BASED_EXPERIENCE must remain False.",
        )
        self.assertFalse(
            self.engine_legacy.use_evidence_based_experience,
            "Legacy engine instance must have use_evidence_based_experience=False.",
        )
        self.assertTrue(
            self.engine_evidence.use_evidence_based_experience,
            "Evidence engine instance must have use_evidence_based_experience=True.",
        )
        self.assertFalse(
            USE_EVIDENCE_BASED_EXPERIENCE,
            "Global feature flag must remain False after engine operations.",
        )

    # ==========================================================================
    # GROUP B: EXPERIENCE SCORING BEHAVIOR & EDGE CASES
    # ==========================================================================

    def test_group_b_bounded_range_duration_saturation(self):
        """
        Verify that candidate tenure meeting or exceeding bounded target (6.0y)
        achieves full duration saturation (D=1.000) with E = 100 * S_agg.
        """
        cand_id = "CAND-01"
        match_result = get_candidate_match_result(cand_id)
        res_ev = self.engine_evidence.score_candidate(match_result, JD_PILOT_01)

        exp_breakdown = res_ev.breakdown["experience_relevance"]
        self.assertEqual(
            exp_breakdown.score,
            89.00,
            "CAND-01 must receive E = 100 * 0.890 * 1.000 = 89.00.",
        )

    def test_group_b_proportional_duration_damping(self):
        """
        Verify that candidate tenure below target receives proportional damping.
        CAND-02: 3.0y / 6.0y = 0.500 -> E = 100 * 0.810 * 0.500 = 40.50.
        CAND-10: 1.5y / 4.0y = 0.375 -> E = 100 * 0.840 * 0.375 = 31.50.
        """
        res_02 = self.engine_evidence.score_candidate(get_candidate_match_result("CAND-02"), JD_PILOT_01)
        res_10 = self.engine_evidence.score_candidate(get_candidate_match_result("CAND-10"), JD_PILOT_02)

        self.assertEqual(res_02.breakdown["experience_relevance"].score, 40.50)
        self.assertEqual(res_10.breakdown["experience_relevance"].score, 31.50)

    def test_group_b_irrelevant_experience_zero_score(self):
        """
        Verify Rule 10: IRRELEVANT decisions receive zero credit for S and D.
        CAND-08, CAND-15, and CAND-23 must all evaluate to E = 0.00.
        """
        for cid, jd in [("CAND-08", JD_PILOT_01), ("CAND-15", JD_PILOT_02), ("CAND-23", JD_PILOT_03)]:
            res = self.engine_evidence.score_candidate(get_candidate_match_result(cid), jd)
            self.assertEqual(
                res.breakdown["experience_relevance"].score,
                0.00,
                f"{cid} with IRRELEVANT background must receive E = 0.00.",
            )

    def test_group_b_missing_date_safeguard(self):
        """
        Verify missing employment dates safeguard: D = 0.000 and E = 0.00,
        while qualitative similarity and evidence summaries remain preserved.
        """
        cand_id = "CAND-06"
        res_ev = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_01)
        exp_breakdown = res_ev.breakdown["experience_relevance"]

        self.assertEqual(exp_breakdown.score, 0.00, "Missing dates must zero Component D score.")
        self.assertIn("diagnostic status", str(exp_breakdown.notes).lower())
        self.assertIn("missing_dates", str(exp_breakdown.notes).lower())

    def test_group_b_g1c_unbounded_experience_safeguard(self):
        """
        Verify Gate 1 Rule C (G1-C) unbounded experience safeguard:
        When JD specifies no duration, D = 0.000 and E = 0.00 with range_status='unspecified'.
        """
        cand_id = "CAND-17"
        res_ev = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_03)
        exp_breakdown = res_ev.breakdown["experience_relevance"]

        self.assertEqual(exp_breakdown.score, 0.00, "G1-C unbounded JD must produce E = 0.00.")

    def test_group_b_multiple_roles_maximum_semantic_similarity(self):
        """
        Verify that candidates with multiple roles in the same domain use
        the maximum calibrated similarity among supporting roles.
        CAND-04: Fintech roles have S=0.85 and S=0.68 -> uses max 0.85.
        """
        cand_id = "CAND-04"
        res_ev = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_01)
        exp_breakdown = res_ev.breakdown["experience_relevance"]

        self.assertEqual(
            exp_breakdown.score,
            82.50,
            "CAND-04 must use max similarity for Fintech (0.85) and Cloud (0.80) -> S_agg = 0.825, E = 82.50.",
        )

    def test_group_b_unsupported_jd_domain_zero_filling(self):
        """
        Verify that preferred JD domains lacking supporting candidate experience
        are zero-filled in S_agg = sum(S_m) / M.
        CAND-03: Fintech = 0.86, Cloud = 0.00 -> S_agg = 0.430, E = 43.00.
        """
        cand_id = "CAND-03"
        res_ev = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_01)
        exp_breakdown = res_ev.breakdown["experience_relevance"]

        self.assertEqual(
            exp_breakdown.score,
            43.00,
            "Unsupported cloud domain must count as 0.0, yielding S_agg = 0.430, E = 43.00.",
        )

    def test_group_b_case_insensitive_domain_deduplication(self):
        """
        Verify that duplicate preferred domains differing only in casing
        are counted only once in the denominator M.
        """
        jd_dup = JobDescriptionObject(
            required_skills=["Python"],
            responsibilities=["APIs"],
            tools_and_technologies=["Docker"],
            experience_requirements=[
                ExperienceRequirement(
                    minimum_years=3.0,
                    maximum_years=5.0,
                    preferred_domains=["Fintech", "fintech", "FINTECH"],
                )
            ],
        )

        match_result = {
            "upload_id": "test_dup",
            "filename": "test.pdf",
            "jd_id": "jd_dup",
            "exact_matching": {"total_required_skills": 1, "matched_required_skills": 1, "unmatched_required_skills": 0, "matches": [{"required_skill": "Python", "matched": True}]},
            "semantic_retrieval": {
                "top_k": 5,
                "responsibilities_retrieval": {"top_k": 5, "results": [{"jd_item_index": 0, "jd_text": "APIs", "matches": [{"similarity": 0.85, "resume_text": "APIs"}]}]},
                "tools_and_technologies_retrieval": {"top_k": 5, "results": [{"jd_item_index": 0, "jd_text": "Docker", "matches": [{"similarity": 0.85, "resume_text": "Docker"}]}]},
            },
            "experience_matching": {
                "duration_factor": 1.0,
                "relevant_duration_years": 4.0,
                "diagnostic_status": "duration_calculated",
                "saturation_target_years": 5.0,
                "range_status": "bounded",
                "aggregated_similarity": 0.80,
                "minimum_years": 3.0,
                "maximum_years": 5.0,
                "experiences": [
                    {
                        "experience_index": 0,
                        "role": "Fintech Dev",
                        "company": "Bank",
                        "decision": "RELEVANT",
                        "relevant": True,
                        "matched_domains": ["Fintech"],
                        "relevance_ratio": 1.0,
                        "relevant_duration_years": 4.0,
                        "semantic_similarity": 0.90,
                        "calibrated_similarity": 0.80,
                        "relevant_work_summary": "Banking APIs",
                        "start_date": "2020-01-01",
                        "end_date": "2024-01-01",
                    }
                ],
            },
        }

        res = self.engine_evidence.score_candidate(match_result, jd_dup)
        exp_breakdown = res.breakdown["experience_relevance"]
        self.assertEqual(exp_breakdown.score, 80.00, "M must be 1, not 3.")

    # ==========================================================================
    # GROUP C: DURATION POOLING (TIME-SLICED WEIGHTED ALGORITHM)
    # ==========================================================================

    def test_group_c_approved_time_sliced_weighted_duration(self):
        """
        Test the approved time-sliced weighted duration algorithm in
        experience_matching_service.calculate_weighted_non_overlapping_duration.
        """
        # Two non-overlapping 2-year periods with ratio 1.0 -> 4.0 years
        periods = [
            (date(2018, 1, 1), date(2020, 1, 1), 1.0),
            (date(2021, 1, 1), date(2023, 1, 1), 1.0),
        ]
        duration = experience_matching_service.calculate_weighted_non_overlapping_duration(periods)
        self.assertAlmostEqual(duration, 4.0, places=1)

    def test_group_c_overlapping_fully_and_partially_relevant_roles(self):
        """
        Verify that overlapping roles use max(r_k) for the intersection slice:
        Role 1: 2021-01-01 to 2024-01-01 (3.0 yrs, ratio 1.0)
        Role 2: 2022-01-01 to 2024-01-01 (2.0 yrs, ratio 0.5)
        Approved behavior: Time slice 2021-2022 is 1.0 * 1.0 = 1.0y.
        Time slice 2022-2024 is 2.0 * max(1.0, 0.5) = 2.0 * 1.0 = 2.0y.
        Total duration = 3.0 years (preserving full credit of fully relevant role).
        """
        periods = [
            (date(2021, 1, 1), date(2024, 1, 1), 1.0),
            (date(2022, 1, 1), date(2024, 1, 1), 0.5),
        ]
        duration = experience_matching_service.calculate_weighted_non_overlapping_duration(periods)
        self.assertAlmostEqual(
            duration,
            3.0,
            places=1,
            msg="Overlapping partially relevant role must not diminish or double-count fully relevant role.",
        )

    def test_group_c_concurrent_intervals_not_double_counted(self):
        """
        Verify that two completely concurrent 3-year roles are not summed to 6.0 years.
        """
        periods = [
            (date(2021, 1, 1), date(2024, 1, 1), 1.0),
            (date(2021, 1, 1), date(2024, 1, 1), 1.0),
        ]
        duration = experience_matching_service.calculate_weighted_non_overlapping_duration(periods)
        self.assertAlmostEqual(
            duration,
            3.0,
            places=1,
            msg="Concurrent identical intervals must evaluate to 3.0 years, not 6.0.",
        )

    def test_group_c_unweighted_union_rejection_and_formula_preservation(self):
        """
        Verify that an unweighted union cannot replace the approved weighted algorithm.
        If a role has ratio 0.5 with no other overlapping roles, it must award
        3.0 * 0.5 = 1.5 years, NOT 3.0 years.
        """
        periods = [(date(2021, 1, 1), date(2024, 1, 1), 0.5)]
        duration = experience_matching_service.calculate_weighted_non_overlapping_duration(periods)
        self.assertAlmostEqual(
            duration,
            1.5,
            places=1,
            msg="Partially relevant role without overlap must be weighted by its ratio (1.5y, not 3.0y).",
        )

    # ==========================================================================
    # GROUP D: PILOT METRIC PREPARATION UTILITIES
    # ==========================================================================

    def test_group_d_precision_at_k_calculation(self):
        """Test Precision@K on deterministic ground truth grades."""
        grades = [3, 2, 1, 0, 3]  # Relevant: indices 0, 1, 4
        p_at_3 = calculate_precision_at_k(grades, 3)  # top 3: [3, 2, 1] -> 2 / 3 = 0.6667
        p_at_5 = calculate_precision_at_k(grades, 5)  # top 5: 3 / 5 = 0.6000

        self.assertEqual(p_at_3, 0.6667)
        self.assertEqual(p_at_5, 0.6000)

    def test_group_d_recall_at_k_calculation_with_exhaustive_denominator(self):
        """
        Test Recall@K where total_relevant is known with mathematical certainty
        from exhaustive cohort grading.
        """
        grades = [3, 2, 1, 0, 3]
        total_relevant = 3  # Two 3s and one 2

        rec_at_2 = calculate_recall_at_k(grades, 2, total_relevant)  # top 2: [3, 2] -> 2/3 = 0.6667
        rec_at_5 = calculate_recall_at_k(grades, 5, total_relevant)  # top 5: [3, 2, 1, 0, 3] -> 3/3 = 1.0000

        self.assertEqual(rec_at_2, 0.6667)
        self.assertEqual(rec_at_5, 1.0000)

    def test_group_d_ndcg_at_k_exponential_gain_and_ideal_discounting(self):
        """
        Test NDCG@K using 2^g - 1 gains and log2(i+1) discounting.
        Perfect ranking [3, 2, 1, 0] must yield NDCG = 1.0000.
        Inverted ranking [0, 1, 2, 3] must yield NDCG < 0.6000.
        """
        perfect = [3, 2, 1, 0]
        inverted = [0, 1, 2, 3]

        ndcg_perfect = calculate_ndcg_at_k(perfect, 4)
        ndcg_inverted = calculate_ndcg_at_k(inverted, 4)

        self.assertEqual(ndcg_perfect, 1.0000)
        self.assertLess(ndcg_inverted, 0.6000)

    def test_group_d_spearman_rank_correlation(self):
        """Test Spearman's rho on identical and inversely monotonic sequences."""
        ranks_x = [1.0, 2.0, 3.0, 4.0, 5.0]
        ranks_y = [1.0, 2.0, 3.0, 4.0, 5.0]
        ranks_inv = [5.0, 4.0, 3.0, 2.0, 1.0]

        rho_perf = calculate_spearman_rho(ranks_x, ranks_y)
        rho_inv = calculate_spearman_rho(ranks_x, ranks_inv)

        self.assertEqual(rho_perf, 1.0000)
        self.assertEqual(rho_inv, -1.0000)

    def test_group_d_tie_rate_definitions_full_cohort_and_top_5(self):
        """
        Test tie rate counting:
        Scores: [100.0, 100.0, 85.0, 50.0, 50.0, 0.0] (N=6, pairs=15).
        Tied pairs: (100,100) and (50,50) -> 2 tied pairs -> 2/15 = 0.1333.
        """
        scores = [100.0, 100.0, 85.0, 50.0, 50.0, 0.0]
        res = calculate_tie_counts_and_rates(scores, k=5)

        self.assertEqual(res["cohort_size"], 6.0)
        self.assertEqual(res["total_pairs"], 15.0)
        self.assertEqual(res["tied_pairs"], 2.0)
        self.assertEqual(res["cohort_tie_rate"], 0.1333)

    def test_group_d_human_relevance_grade_mapping_and_advisory_thresholds(self):
        """
        Verify human grade binary mapping (Grade >= 2 is relevant).
        """
        self.assertEqual(human_grade_to_binary(3), 1)
        self.assertEqual(human_grade_to_binary(2), 1)
        self.assertEqual(human_grade_to_binary(1), 0)
        self.assertEqual(human_grade_to_binary(0), 0)

    # ==========================================================================
    # GROUP E: EXPLANATION, TRACEABILITY, AND PROVENANCE
    # ==========================================================================

    def test_group_e_evidence_source_traceability(self):
        """
        Verify that evidence items in Component D contain all required provenance
        fields: supporting_role, supporting_company, calibrated_similarity, and reason.
        """
        cand_id = "CAND-01"
        res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_01)
        evidence = res.breakdown["experience_relevance"].evidence

        self.assertGreater(len(evidence), 0, "Component D must produce evidence items.")
        item = evidence[0]
        self.assertIn("supporting_role", item)
        self.assertIn("supporting_company", item)
        self.assertIn("calibrated_similarity", item)
        self.assertIn("reason", item)
        self.assertEqual(item["supporting_role"], "Principal Cloud Architect")

    def test_group_e_missing_date_diagnostics(self):
        """
        Verify that candidates with missing dates receive explicit diagnostic
        reporting in their ranking breakdown notes.
        """
        cand_id = "CAND-06"
        res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_01)
        notes = res.breakdown["experience_relevance"].notes
        self.assertIn("missing_dates", str(notes))

    def test_group_e_g1c_diagnostic_status_and_alerts(self):
        """
        Verify that G1-C unbounded JDs produce clear diagnostic notices
        explaining that duration is unspecified.
        """
        cand_id = "CAND-17"
        res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_03)
        notes = res.breakdown["experience_relevance"].notes
        self.assertIn("unspecified", str(notes))

    def test_group_e_zero_score_vs_missing_information_distinction(self):
        """
        Verify proper distinction between an unqualified candidate (CAND-08,
        no_relevant_experience) and a qualified candidate with missing dates
        (CAND-06, missing_dates). Both score 0.00 in Component D, but diagnostic
        provenance differs.
        """
        res_08 = self.engine_evidence.score_candidate(get_candidate_match_result("CAND-08"), JD_PILOT_01)
        res_06 = self.engine_evidence.score_candidate(get_candidate_match_result("CAND-06"), JD_PILOT_01)

        note_08 = str(res_08.breakdown["experience_relevance"].notes)
        note_06 = str(res_06.breakdown["experience_relevance"].notes)

        self.assertIn("no_relevant_experience", note_08)
        self.assertIn("missing_dates", note_06)

    def test_group_e_g1c_domain_evidence_preservation_despite_zero_duration(self):
        """
        Verify that under G1-C, although D = 0.000 and E = 0.00, the candidate's
        domain evidence and high calibrated similarity (0.88) remain preserved
        in the evidence payload for recruiter auditing.
        """
        cand_id = "CAND-17"
        res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_03)
        evidence = res.breakdown["experience_relevance"].evidence

        self.assertGreater(len(evidence), 0)
        # Find item for Cloud Infrastructure
        cloud_item = next((item for item in evidence if item["criterion"] == "Cloud Infrastructure"), None)
        self.assertIsNotNone(cloud_item)
        self.assertEqual(cloud_item["calibrated_similarity"], 0.88)
        self.assertEqual(cloud_item["supporting_role"], "Principal Systems Architect")


if __name__ == "__main__":
    unittest.main()
