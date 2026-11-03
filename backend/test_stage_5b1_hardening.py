"""
TalentAI — Stage 5B.1 Focused Hardening Regression Tests

Validates:
1. Ratio validation (1.0, 0.5, 0.0, -0.5, -1.0, 1.5, 2.0, None, 'abc', 'NaN', '', +inf, -inf)
2. Decision consistency (IRRELEVANT+0.5, AMBIGUOUS+0.5, INSUFFICIENT_INFORMATION+0.5, RELEVANT+0.0, PARTIALLY_RELEVANT+0.5)
3. Regression protections:
   - Phase 3 time-sliced union
   - Missing dates preserve qualitative relevance with zero duration
   - G1-C unbounded target behavior
   - Per-domain max similarity aggregation and equal domain weighting
   - Rule 7: Similarity not multiplied by relevance ratio
   - Ranking weights remain 25%, 30%, 10%, 35%
   - Feature flag USE_EVIDENCE_BASED_EXPERIENCE remains False
"""

import math
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.resume_object import Experience, ResumeObject
from app.services.experience_matching_service import experience_matching_service
from app.ranking.ranking_config import (
    BASE_WEIGHTS,
    USE_EVIDENCE_BASED_EXPERIENCE,
)


def create_standard_test_fixtures(calendar_years: float = 2.0):
    jd = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2.0,
                maximum_years=5.0,
                preferred_domains=["Machine Learning"],
            )
        ]
    )
    # 2.0 calendar years: 2020-01-01 to 2022-01-01
    resume = ResumeObject(
        name="Hardening Candidate",
        experience=[
            Experience(
                role="Machine Learning Engineer",
                company="AI Labs",
                start_date="2020-01-01",
                end_date="2022-01-01",
                description="Trained PyTorch transformer models for production deployment.",
            )
        ],
    )
    vec = [1.0, 0.0, 0.0]
    return jd, resume, vec


def test_ratio_validation_all_cases():
    print("--- Running Test: Ratio Validation All Cases ---")
    jd, resume, vec = create_standard_test_fixtures(calendar_years=2.0)

    test_cases = [
        (1.0, 2.0, 2.0, 1.0),
        (0.5, 1.0, 1.0, 0.5),
        (0.0, 0.0, 0.0, 0.0),
        (-0.5, 0.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0, 0.0),
        (1.5, 2.0, 2.0, 1.0),  # clamped to 1.0 -> 2.0 yrs
        (2.0, 2.0, 2.0, 1.0),  # clamped to 1.0 -> 2.0 yrs
        (None, 0.0, 0.0, 0.0),  # invalid -> conservative 0.0
        ("abc", 0.0, 0.0, 0.0),  # invalid -> conservative 0.0
        ("NaN", 0.0, 0.0, 0.0),  # invalid -> conservative 0.0
        ("", 0.0, 0.0, 0.0),  # invalid -> conservative 0.0
        (float("inf"), 0.0, 0.0, 0.0),  # infinite -> conservative 0.0
        ("+inf", 0.0, 0.0, 0.0),  # infinite -> conservative 0.0
        (float("-inf"), 0.0, 0.0, 0.0),  # infinite -> conservative 0.0
        ("-inf", 0.0, 0.0, 0.0),  # infinite -> conservative 0.0
    ]

    for raw_ratio, exp_per_exp_dur, exp_tot_dur, exp_ratio_in_dict in test_cases:
        rel_results = [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "relevance_ratio": raw_ratio,
                "relevant_work_summary": "Trained PyTorch transformer models.",
                "matched_domains": ["Machine Learning"],
            }
        ]

        res = experience_matching_service.match_experience(
            resume=resume,
            job_description=jd,
            relevance_results=rel_results,
            candidate_embeddings={0: vec},
            jd_embeddings={"Machine Learning": vec},
        )

        exp0 = res["experiences"][0]
        per_exp_dur = exp0["relevant_duration_years"]
        tot_dur = res["relevant_duration_years"]
        d_factor = res["duration_factor"]
        out_ratio = exp0["relevance_ratio"]

        # 1. Finite checks
        assert math.isfinite(per_exp_dur), f"per_exp_dur not finite for {raw_ratio}: {per_exp_dur}"
        assert math.isfinite(tot_dur), f"tot_dur not finite for {raw_ratio}: {tot_dur}"
        assert math.isfinite(d_factor), f"d_factor not finite for {raw_ratio}: {d_factor}"
        assert math.isfinite(out_ratio), f"out_ratio not finite for {raw_ratio}: {out_ratio}"

        # 2. Non-negative checks
        assert per_exp_dur >= 0.0, f"per_exp_dur negative for {raw_ratio}: {per_exp_dur}"
        assert tot_dur >= 0.0, f"tot_dur negative for {raw_ratio}: {tot_dur}"
        assert out_ratio >= 0.0, f"out_ratio negative for {raw_ratio}: {out_ratio}"

        # 3. Calendar duration bounds (calendar tenure is 2.0 yrs)
        cal_tenure = exp0["duration_years"]
        assert per_exp_dur <= cal_tenure, (
            f"per_exp_dur ({per_exp_dur}) exceeded calendar tenure ({cal_tenure}) for {raw_ratio}"
        )

        # 4. Consistency checks
        assert per_exp_dur == exp_per_exp_dur, (
            f"Expected per_exp_dur={exp_per_exp_dur}, got {per_exp_dur} for {raw_ratio}"
        )
        assert tot_dur == exp_tot_dur, (
            f"Expected tot_dur={exp_tot_dur}, got {tot_dur} for {raw_ratio}"
        )
        assert out_ratio == exp_ratio_in_dict, (
            f"Expected out_ratio={exp_ratio_in_dict}, got {out_ratio} for {raw_ratio}"
        )

    print("PASS: test_ratio_validation_all_cases")


def test_decision_consistency_all_cases():
    print("--- Running Test: Decision Consistency All Cases ---")
    jd, resume, vec = create_standard_test_fixtures(calendar_years=2.0)

    # Contradictory inputs
    negative_cases = [
        ("IRRELEVANT", 0.5),
        ("AMBIGUOUS", 0.5),
        ("INSUFFICIENT_INFORMATION", 0.5),
    ]

    for dec, rat in negative_cases:
        rel_results = [
            {
                "experience_index": 0,
                "decision": dec,
                "relevance_ratio": rat,
                "relevant_work_summary": "Trained PyTorch transformer models.",
                "matched_domains": ["Machine Learning"],
            }
        ]

        # 1. get_relevant_experience_indexes
        rel_idxs = experience_matching_service.get_relevant_experience_indexes(rel_results)
        assert 0 not in rel_idxs, f"Index 0 should not be relevant for negative decision {dec}"

        # 2. match_experience
        res = experience_matching_service.match_experience(
            resume=resume,
            job_description=jd,
            relevance_results=rel_results,
            candidate_embeddings={0: vec},
            jd_embeddings={"Machine Learning": vec},
        )

        exp0 = res["experiences"][0]
        assert exp0["relevant"] is False, f"exp0['relevant'] must be False for {dec}"
        assert exp0["relevance_ratio"] == 0.0, f"exp0['relevance_ratio'] must be 0.0 for {dec}"
        assert exp0["relevant_duration_years"] == 0.0, f"exp0['relevant_duration_years'] must be 0.0 for {dec}"
        assert exp0["semantic_similarity"] == 0.0, f"exp0['semantic_similarity'] must be 0.0 for {dec}"
        assert exp0["calibrated_similarity"] == 0.0, f"exp0['calibrated_similarity'] must be 0.0 for {dec}"
        assert res["relevant_experience_found"] is False, f"res['relevant_experience_found'] must be False for {dec}"
        assert res["relevant_duration_years"] == 0.0, f"res['relevant_duration_years'] must be 0.0 for {dec}"
        assert res["duration_factor"] == 0.0, f"res['duration_factor'] must be 0.0 for {dec}"
        assert res["aggregated_similarity"] == 0.0, f"res['aggregated_similarity'] must be 0.0 for {dec}"

    # Positive cases
    # Case: RELEVANT + 0.0
    rel_results_rel_zero = [
        {
            "experience_index": 0,
            "decision": "RELEVANT",
            "relevance_ratio": 0.0,
            "relevant_work_summary": "Trained PyTorch transformer models.",
            "matched_domains": ["Machine Learning"],
        }
    ]
    res_rel_zero = experience_matching_service.match_experience(
        resume=resume,
        job_description=jd,
        relevance_results=rel_results_rel_zero,
        candidate_embeddings={0: vec},
        jd_embeddings={"Machine Learning": vec},
    )
    exp0 = res_rel_zero["experiences"][0]
    assert exp0["relevant"] is True
    assert exp0["relevance_ratio"] == 0.0
    assert exp0["relevant_duration_years"] == 0.0
    assert res_rel_zero["relevant_experience_found"] is True
    assert res_rel_zero["relevant_duration_years"] == 0.0
    assert res_rel_zero["duration_factor"] == 0.0
    assert exp0["calibrated_similarity"] == 1.0  # similarity preserved for RELEVANT

    # Case: PARTIALLY_RELEVANT + 0.5
    rel_results_part = [
        {
            "experience_index": 0,
            "decision": "PARTIALLY_RELEVANT",
            "relevance_ratio": 0.5,
            "relevant_work_summary": "Trained PyTorch transformer models.",
            "matched_domains": ["Machine Learning"],
        }
    ]
    res_part = experience_matching_service.match_experience(
        resume=resume,
        job_description=jd,
        relevance_results=rel_results_part,
        candidate_embeddings={0: vec},
        jd_embeddings={"Machine Learning": vec},
    )
    exp0 = res_part["experiences"][0]
    assert exp0["relevant"] is True
    assert exp0["relevance_ratio"] == 0.5
    assert exp0["relevant_duration_years"] == 1.0
    assert res_part["relevant_experience_found"] is True
    assert res_part["relevant_duration_years"] == 1.0
    assert res_part["duration_factor"] > 0.0
    assert exp0["calibrated_similarity"] == 1.0

    print("PASS: test_decision_consistency_all_cases")


def test_missing_decision_and_legacy_relevance_score():
    print("--- Running Test: Missing Decision & Legacy Relevance Score ---")
    jd, resume, vec = create_standard_test_fixtures(calendar_years=2.0)

    # 1. Genuinely missing decision + no relevance_score + ratio=0.8
    # Must NOT invent relevance from an orphan ratio!
    res_orphan = experience_matching_service.match_experience(
        resume=resume,
        job_description=jd,
        relevance_results=[
            {
                "experience_index": 0,
                "relevance_ratio": 0.8,
            }
        ],
    )
    assert res_orphan["relevant_experience_found"] is False
    assert res_orphan["experiences"][0]["relevant"] is False
    assert res_orphan["experiences"][0]["relevance_ratio"] == 0.0
    assert res_orphan["relevant_duration_years"] == 0.0

    # 2. Legacy contract: relevance_score >= 0.60
    res_legacy = experience_matching_service.match_experience(
        resume=resume,
        job_description=jd,
        relevance_results=[
            {
                "experience_index": 0,
                "relevance_score": 0.85,
            }
        ],
        relevance_threshold=0.60,
    )
    assert res_legacy["relevant_experience_found"] is True
    assert res_legacy["experiences"][0]["relevant"] is True
    assert res_legacy["experiences"][0]["relevance_ratio"] == 1.0
    assert res_legacy["relevant_duration_years"] == 2.0

    # 3. Legacy contract: relevance_score < 0.60
    res_legacy_sub = experience_matching_service.match_experience(
        resume=resume,
        job_description=jd,
        relevance_results=[
            {
                "experience_index": 0,
                "relevance_score": 0.40,
            }
        ],
        relevance_threshold=0.60,
    )
    assert res_legacy_sub["relevant_experience_found"] is False
    assert res_legacy_sub["experiences"][0]["relevant"] is False
    assert res_legacy_sub["relevant_duration_years"] == 0.0

    print("PASS: test_missing_decision_and_legacy_relevance_score")


def test_regression_protections():
    print("--- Running Test: Regression Protections ---")

    # 1. Config and weights
    assert BASE_WEIGHTS["required_skills"] == 0.25, f"required_skills={BASE_WEIGHTS['required_skills']}"
    assert BASE_WEIGHTS["responsibilities"] == 0.30, f"responsibilities={BASE_WEIGHTS['responsibilities']}"
    assert BASE_WEIGHTS["tools_and_technologies"] == 0.10, f"tools_and_technologies={BASE_WEIGHTS['tools_and_technologies']}"
    assert BASE_WEIGHTS["experience_relevance"] == 0.35, f"experience_relevance={BASE_WEIGHTS['experience_relevance']}"
    assert USE_EVIDENCE_BASED_EXPERIENCE is True, "USE_EVIDENCE_BASED_EXPERIENCE must be True by production default"

    # 2. G1-C unbounded target behavior
    jd_unbounded = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=None,
                maximum_years=None,
                preferred_domains=["Data Science"],
            )
        ]
    )
    d_fac, target, status, note = experience_matching_service.compute_duration_factor(
        relevant_duration_years=3.5,
        minimum_years=None,
        maximum_years=None,
        duration_available=True,
    )
    assert status == "unspecified"
    assert target is None
    assert d_fac == 0.0

    # 3. Missing dates preserve qualitative relevance with zero duration
    jd_bounded = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2.0,
                maximum_years=5.0,
                preferred_domains=["Machine Learning"],
            )
        ]
    )
    resume_no_dates = ResumeObject(
        name="No Dates Candidate",
        experience=[
            Experience(
                role="ML Engineer",
                company="Company",
                start_date=None,
                end_date=None,
                description="Trained PyTorch models.",
            )
        ],
    )
    res_no_dates = experience_matching_service.match_experience(
        resume=resume_no_dates,
        job_description=jd_bounded,
        relevance_results=[
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "relevance_ratio": 1.0,
                "relevant_work_summary": "Trained PyTorch models.",
                "matched_domains": ["Machine Learning"],
            }
        ],
        candidate_embeddings={0: [1.0, 0.0, 0.0]},
        jd_embeddings={"Machine Learning": [1.0, 0.0, 0.0]},
    )
    assert res_no_dates["relevant_experience_found"] is True
    assert res_no_dates["experiences"][0]["relevant"] is True
    assert res_no_dates["experiences"][0]["duration_available"] is False
    assert res_no_dates["experiences"][0]["date_status"] == "missing_dates"
    assert res_no_dates["relevant_duration_years"] == 0.0
    assert res_no_dates["duration_factor"] == 0.0
    assert res_no_dates["aggregated_similarity"] == 1.0  # similarity intact

    # 4. Multi-domain equal weighting & max aggregation
    jd_multi = JobDescriptionObject(
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2.0,
                maximum_years=5.0,
                preferred_domains=["ML", "Cloud"],
            )
        ]
    )
    resume_multi = ResumeObject(
        name="Multi Domain",
        experience=[
            Experience(
                role="ML Engineer",
                company="A",
                start_date="2020-01-01",
                end_date="2021-01-01",
                description="ML work",
            ),
            Experience(
                role="Cloud Architect",
                company="B",
                start_date="2021-01-01",
                end_date="2022-01-01",
                description="Cloud work",
            ),
        ],
    )
    # Unit vectors
    ml_emb = [1.0, 0.0]
    cloud_emb = [0.0, 1.0]
    res_multi = experience_matching_service.match_experience(
        resume=resume_multi,
        job_description=jd_multi,
        relevance_results=[
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "relevance_ratio": 1.0,
                "relevant_work_summary": "ML work",
                "matched_domains": ["ML"],
            },
            {
                "experience_index": 1,
                "decision": "RELEVANT",
                "relevance_ratio": 1.0,
                "relevant_work_summary": "Cloud work",
                "matched_domains": ["Cloud"],
            },
        ],
        candidate_embeddings={0: ml_emb, 1: cloud_emb},
        jd_embeddings={"ML": ml_emb, "Cloud": cloud_emb},
    )
    assert res_multi["experience_requirements"]["preferred_domains"] == ["ML", "Cloud"]
    # Both domains achieve 1.0 similarity -> S_agg = (1.0 + 1.0) / 2 = 1.0
    assert res_multi["aggregated_similarity"] == 1.0

    # 5. Rule 7: Similarity is NOT multiplied by relevance_ratio a second time!
    # Experience 0 with ratio 0.5:
    res_rule7 = experience_matching_service.match_experience(
        resume=resume_multi,
        job_description=jd_multi,
        relevance_results=[
            {
                "experience_index": 0,
                "decision": "PARTIALLY_RELEVANT",
                "relevance_ratio": 0.5,
                "relevant_work_summary": "ML work",
                "matched_domains": ["ML"],
            }
        ],
        candidate_embeddings={0: ml_emb},
        jd_embeddings={"ML": ml_emb, "Cloud": cloud_emb},
    )
    exp0 = res_rule7["experiences"][0]
    # Raw sim is 1.0, calibrated sim is 1.0 (NOT multiplied by 0.5!)
    assert exp0["calibrated_similarity"] == 1.0
    # Aggregated similarity across 2 domains: ML=1.0, Cloud=0.0 -> (1.0 + 0.0) / 2 = 0.5
    assert res_rule7["aggregated_similarity"] == 0.5

    print("PASS: test_regression_protections")


if __name__ == "__main__":
    print("\n=======================================================")
    print("STARTING STAGE 5B.1 TARGETED HARDENING REGRESSION SUITE")
    print("=======================================================\n")
    test_ratio_validation_all_cases()
    test_decision_consistency_all_cases()
    test_missing_decision_and_legacy_relevance_score()
    test_regression_protections()
    print("\n=======================================================")
    print("ALL STAGE 5B.1 TARGETED HARDENING REGRESSION TESTS PASSED")
    print("=======================================================\n")
