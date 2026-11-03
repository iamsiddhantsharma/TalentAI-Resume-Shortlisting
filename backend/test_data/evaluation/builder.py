"""
TalentAI — Phase 9.2: Synthetic Fixture & Match Result Builder

Constructs deterministic, version-controlled JobDescriptionObject and
ResumeMatchResult payloads for evaluating ranking quality without live
LLM or embedding model dependencies.
"""

import json
from math import sqrt
from pathlib import Path
from typing import Any

from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
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

FIXTURE_DIR = Path(__file__).resolve().parent


def load_benchmark_jds() -> dict[str, JobDescriptionObject]:
    """
    Load all version-controlled benchmark Job Descriptions from JSON fixtures.
    """
    jd_file = FIXTURE_DIR / "job_descriptions.json"
    with open(jd_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    jds: dict[str, JobDescriptionObject] = {}
    for jd_key, jd_dict in data.items():
        exp_reqs = [
            ExperienceRequirement(
                minimum_years=r.get("minimum_years"),
                maximum_years=r.get("maximum_years"),
                preferred_domains=r.get("preferred_domains", []),
            )
            for r in jd_dict.get("experience_requirements", [])
        ]
        jds[jd_key] = JobDescriptionObject(
            required_skills=jd_dict.get("required_skills", []),
            responsibilities=jd_dict.get("responsibilities", []),
            tools_and_technologies=jd_dict.get("tools_and_technologies", []),
            experience_requirements=exp_reqs,
        )
    return jds


def load_ground_truth_annotations() -> tuple[dict[str, int], list[str]]:
    """
    Load ground-truth human annotations. Returns (annotations_dict, technical_failed_filenames).
    """
    gt_file = FIXTURE_DIR / "ground_truth_annotations.json"
    with open(gt_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    annotations: dict[str, int] = {
        fn: entry["relevance_grade"]
        for fn, entry in data.get("candidate_annotations", {}).items()
    }
    failed_fns = list(data.get("technical_failure_candidates", {}).keys())
    return annotations, failed_fns


def make_orthogonal_vector(similarity: float, dim: int = 1024) -> list[float]:
    """
    Construct a deterministic unit-normalized vector whose cosine similarity
    with base vector [1.0, 0.0, ...] is exactly `similarity`.
    """
    clamped = max(-1.0, min(1.0, similarity))
    y = sqrt(max(0.0, 1.0 - clamped * clamped))
    vec = [0.0] * dim
    vec[0] = clamped
    vec[1] = y
    return vec


def build_semantic_section_retrieval(
    items: list[tuple[int, str, float, str]],
    section_name: str,
    top_k: int = 5,
) -> SemanticSectionRetrieval:
    """
    Build a SemanticSectionRetrieval object with deterministic evidence matches.
    items: list of (jd_item_index, jd_text, raw_similarity, resume_section)
    """
    req_results: list[SemanticRetrievalRequirementResult] = []
    for idx, text, sim, r_sec in items:
        match_item = SemanticEvidenceMatchItem(
            jd_section=section_name,
            jd_item_index=idx,
            jd_text=text,
            resume_section=r_sec,
            resume_item_index=0,
            resume_text=f"Supporting passage for {text} with similarity {sim:.2f}",
            similarity=float(sim),
        )
        req_results.append(
            SemanticRetrievalRequirementResult(
                jd_section=section_name,
                jd_item_index=idx,
                jd_text=text,
                matches=[match_item] if sim > 0.0 else [],
            )
        )
    return SemanticSectionRetrieval(top_k=top_k, results=req_results)


def build_synthetic_cohort(jd: JobDescriptionObject, jd_id: str = "jd_01_fullstack_cloud") -> list[ResumeMatchResult]:
    """
    Construct the complete synthetic candidate cohort covering Scenarios SC-01 through SC-17.
    """
    cohort: list[ResumeMatchResult] = []

    # --------------------------------------------------------------------------
    # SC-01: CAND-01 Strong Fit (Alex Rivera)
    # --------------------------------------------------------------------------
    exact_01 = ExactMatchingResult(
        total_required_skills=4,
        matched_required_skills=4,
        unmatched_required_skills=0,
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=True, resume_skill="Python", match_type="exact"),
            ExactSkillMatchItem(required_skill="FastAPI", matched=True, resume_skill="FastAPI", match_type="exact"),
            ExactSkillMatchItem(required_skill="Docker", matched=True, resume_skill="Docker", match_type="exact"),
            ExactSkillMatchItem(required_skill="PostgreSQL", matched=True, resume_skill="PostgreSQL", match_type="exact"),
        ],
        status="complete",
    )
    resp_items_01 = [
        (0, jd.responsibilities[0], 0.95, "experience"),
        (1, jd.responsibilities[1], 0.92, "projects"),
        (2, jd.responsibilities[2], 0.90, "projects"),
    ]
    tools_items_01 = [
        (0, jd.tools_and_technologies[0], 0.90, "projects"),
        (1, jd.tools_and_technologies[1], 0.88, "projects"),
        (2, jd.tools_and_technologies[2], 0.92, "projects"),
    ]
    sem_01 = SemanticRetrievalResult(
        responsibilities_retrieval=build_semantic_section_retrieval(resp_items_01, "responsibilities"),
        tools_and_technologies_retrieval=build_semantic_section_retrieval(tools_items_01, "tools_and_technologies"),
        status="complete",
    )
    exp_01 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]),
        experience_requirement_present=True,
        relevant_experience_found=True,
        relevant_duration_years=4.5,
        minimum_years=3.0,
        maximum_years=6.0,
        minimum_duration_satisfied=True,
        maximum_duration_exceeded=False,
        diagnostic_status="duration_satisfied",
        status="complete",
        experiences=[
            CandidateExperienceItem(
                experience_index=0,
                role="Senior Cloud Architect",
                company="Apex Cloud",
                decision="RELEVANT",
                relevant=True,
                matched_domains=["Cloud Systems"],
                duration_years=2.5,
                duration_available=True,
            ),
            CandidateExperienceItem(
                experience_index=1,
                role="Fintech Platform Engineer",
                company="Nexus Pay",
                decision="RELEVANT",
                relevant=True,
                matched_domains=["Fintech"],
                duration_years=2.0,
                duration_available=True,
            ),
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_01_strong.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_01,
            experience_matching=exp_01,
        )
    )

    # --------------------------------------------------------------------------
    # SC-02: CAND-02 Partial Fit (Jordan Lee)
    # --------------------------------------------------------------------------
    exact_02 = ExactMatchingResult(
        total_required_skills=4,
        matched_required_skills=2,
        unmatched_required_skills=2,
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=True, resume_skill="Python", match_type="exact"),
            ExactSkillMatchItem(required_skill="FastAPI", matched=False),
            ExactSkillMatchItem(required_skill="Docker", matched=True, resume_skill="Docker", match_type="exact"),
            ExactSkillMatchItem(required_skill="PostgreSQL", matched=False),
        ],
        status="complete",
    )
    resp_items_02 = [
        (0, jd.responsibilities[0], 0.78, "experience"),
        (1, jd.responsibilities[1], 0.72, "projects"),
        (2, jd.responsibilities[2], 0.60, "projects"),  # below 0.65 threshold
    ]
    tools_items_02 = [
        (0, jd.tools_and_technologies[0], 0.82, "projects"),
        (1, jd.tools_and_technologies[1], 0.60, "projects"),  # below 0.65 threshold
        (2, jd.tools_and_technologies[2], 0.50, "projects"),  # below 0.65 threshold
    ]
    sem_02 = SemanticRetrievalResult(
        responsibilities_retrieval=build_semantic_section_retrieval(resp_items_02, "responsibilities"),
        tools_and_technologies_retrieval=build_semantic_section_retrieval(tools_items_02, "tools_and_technologies"),
        status="complete",
    )
    exp_02 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]),
        experience_requirement_present=True,
        relevant_experience_found=True,
        relevant_duration_years=3.5,
        minimum_years=3.0,
        maximum_years=6.0,
        minimum_duration_satisfied=True,
        maximum_duration_exceeded=False,
        status="complete",
        experiences=[
            CandidateExperienceItem(
                experience_index=0,
                role="Fintech Developer",
                company="PayCorp",
                decision="RELEVANT",
                relevant=True,
                matched_domains=["Fintech"],
                duration_years=3.5,
                duration_available=True,
            )
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_02_partial.pdf",
            exact_matching=exact_02,
            semantic_retrieval=sem_02,
            experience_matching=exp_02,
        )
    )

    # --------------------------------------------------------------------------
    # SC-03: CAND-03 Weak Fit (Taylor Swift-Coder)
    # --------------------------------------------------------------------------
    exact_03 = ExactMatchingResult(
        total_required_skills=4,
        matched_required_skills=1,
        unmatched_required_skills=3,
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=True, resume_skill="Python", match_type="exact"),
            ExactSkillMatchItem(required_skill="FastAPI", matched=False),
            ExactSkillMatchItem(required_skill="Docker", matched=False),
            ExactSkillMatchItem(required_skill="PostgreSQL", matched=False),
        ],
        status="complete",
    )
    resp_items_03 = [
        (0, jd.responsibilities[0], 0.62, "experience"),
        (1, jd.responsibilities[1], 0.55, "projects"),
        (2, jd.responsibilities[2], 0.40, "projects"),
    ]
    tools_items_03 = [
        (0, jd.tools_and_technologies[0], 0.60, "projects"),
        (1, jd.tools_and_technologies[1], 0.50, "projects"),
        (2, jd.tools_and_technologies[2], 0.45, "projects"),
    ]
    sem_03 = SemanticRetrievalResult(
        responsibilities_retrieval=build_semantic_section_retrieval(resp_items_03, "responsibilities"),
        tools_and_technologies_retrieval=build_semantic_section_retrieval(tools_items_03, "tools_and_technologies"),
        status="complete",
    )
    exp_03 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]),
        experience_requirement_present=True,
        relevant_experience_found=False,
        relevant_duration_years=0.0,
        status="complete",
        experiences=[
            CandidateExperienceItem(
                experience_index=0,
                role="Marketing Specialist",
                company="Retail Brand",
                decision="IRRELEVANT",
                relevant=False,
                matched_domains=[],
            )
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_03_weak.pdf",
            exact_matching=exact_03,
            semantic_retrieval=sem_03,
            experience_matching=exp_03,
        )
    )

    # --------------------------------------------------------------------------
    # SC-04: CAND-04 Valid Zero Fit (Morgan Vance)
    # --------------------------------------------------------------------------
    exact_04 = ExactMatchingResult(
        total_required_skills=4,
        matched_required_skills=0,
        unmatched_required_skills=4,
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=False),
            ExactSkillMatchItem(required_skill="FastAPI", matched=False),
            ExactSkillMatchItem(required_skill="Docker", matched=False),
            ExactSkillMatchItem(required_skill="PostgreSQL", matched=False),
        ],
        status="complete",
    )
    resp_items_04 = [
        (0, jd.responsibilities[0], 0.30, "experience"),
        (1, jd.responsibilities[1], 0.25, "projects"),
        (2, jd.responsibilities[2], 0.20, "projects"),
    ]
    tools_items_04 = [
        (0, jd.tools_and_technologies[0], 0.35, "projects"),
        (1, jd.tools_and_technologies[1], 0.20, "projects"),
        (2, jd.tools_and_technologies[2], 0.15, "projects"),
    ]
    sem_04 = SemanticRetrievalResult(
        responsibilities_retrieval=build_semantic_section_retrieval(resp_items_04, "responsibilities"),
        tools_and_technologies_retrieval=build_semantic_section_retrieval(tools_items_04, "tools_and_technologies"),
        status="complete",
    )
    exp_04 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]),
        experience_requirement_present=True,
        relevant_experience_found=False,
        relevant_duration_years=0.0,
        status="complete",
        experiences=[
            CandidateExperienceItem(
                experience_index=0,
                role="Graphic Designer",
                company="Design Studio",
                decision="IRRELEVANT",
                relevant=False,
                matched_domains=[],
            )
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_04_zero.pdf",
            exact_matching=exact_04,
            semantic_retrieval=sem_04,
            experience_matching=exp_04,
        )
    )

    # --------------------------------------------------------------------------
    # SC-05: CAND-05 Skill Noise / Distractors (Samir Patel)
    # --------------------------------------------------------------------------
    exact_05 = ExactMatchingResult(
        total_required_skills=4,
        matched_required_skills=3,
        unmatched_required_skills=1,
        matches=[
            ExactSkillMatchItem(required_skill="Python", matched=True, resume_skill="Python", match_type="exact"),
            ExactSkillMatchItem(required_skill="FastAPI", matched=True, resume_skill="FastAPI", match_type="exact"),
            ExactSkillMatchItem(required_skill="Docker", matched=True, resume_skill="Docker", match_type="exact"),
            ExactSkillMatchItem(required_skill="PostgreSQL", matched=False),
        ],
        status="complete",
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_05_skill_noise.pdf",
            exact_matching=exact_05,
            semantic_retrieval=sem_02,
            experience_matching=exp_02,
        )
    )

    # --------------------------------------------------------------------------
    # SC-06: CAND-06 Tools in Experience Only (Riley Quinn)
    # --------------------------------------------------------------------------
    tools_items_exp_only = [
        (0, jd.tools_and_technologies[0], 0.90, "experience"),  # In experience, not projects!
        (1, jd.tools_and_technologies[1], 0.85, "experience"),
        (2, jd.tools_and_technologies[2], 0.88, "experience"),
    ]
    sem_06 = SemanticRetrievalResult(
        responsibilities_retrieval=build_semantic_section_retrieval(resp_items_01, "responsibilities"),
        # Under section routing, tools in experience do not qualify for project score (0.0), but establish valid evidence
        tools_and_technologies_retrieval=build_semantic_section_retrieval(tools_items_exp_only, "tools_and_technologies"),
        status="complete",
    )
    exp_06 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(
            minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]
        ),
        experience_requirement_present=True,
        relevant_experience_found=True,
        relevant_duration_years=4.5,
        minimum_years=3.0,
        maximum_years=6.0,
        minimum_duration_satisfied=True,
        maximum_duration_exceeded=False,
        diagnostic_status="duration_satisfied",
        status="complete",
        experiences=[
            CandidateExperienceItem(
                experience_index=0,
                role="Senior Cloud Architect",
                company="Apex Cloud",
                description="Deployed containerized microservices across Docker and Kubernetes clusters with PostgreSQL persistence.",
                decision="RELEVANT",
                relevant=True,
                matched_domains=["Cloud Systems"],
                duration_years=2.5,
                duration_available=True,
            ),
            CandidateExperienceItem(
                experience_index=1,
                role="Fintech Platform Engineer",
                company="Nexus Pay",
                description="Engineered high-throughput payments architecture and API microservices.",
                decision="RELEVANT",
                relevant=True,
                matched_domains=["Fintech"],
                duration_years=2.0,
                duration_available=True,
            ),
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_06_tools_in_exp_only.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_06,
            experience_matching=exp_06,
        )
    )

    # --------------------------------------------------------------------------
    # SC-07: CAND-07 Responsibilities in Projects Only (Casey Morgan)
    # --------------------------------------------------------------------------
    resp_items_proj_only = [
        (0, jd.responsibilities[0], 0.85, "projects"),
        (1, jd.responsibilities[1], 0.80, "projects"),
        (2, jd.responsibilities[2], 0.75, "projects"),
    ]
    sem_07 = SemanticRetrievalResult(
        responsibilities_retrieval=build_semantic_section_retrieval(resp_items_proj_only, "responsibilities"),
        tools_and_technologies_retrieval=build_semantic_section_retrieval(tools_items_01, "tools_and_technologies"),
        status="complete",
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_07_resp_in_proj_only.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_07,
            experience_matching=exp_04,  # zero work experience
        )
    )

    # --------------------------------------------------------------------------
    # SC-08: CAND-08 Multi-unrelated Experience Non-dilution (Dakota Chen)
    # --------------------------------------------------------------------------
    exp_08 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]),
        experience_requirement_present=True,
        relevant_experience_found=True,
        relevant_duration_years=4.0,
        status="complete",
        experiences=[
            CandidateExperienceItem(experience_index=0, role="Fintech Lead", company="PaySafe", decision="RELEVANT", relevant=True, matched_domains=["Fintech"]),
            CandidateExperienceItem(experience_index=1, role="Barista", company="Coffee House", decision="IRRELEVANT", relevant=False, matched_domains=[]),
            CandidateExperienceItem(experience_index=2, role="Math Tutor", company="Self", decision="IRRELEVANT", relevant=False, matched_domains=[]),
            CandidateExperienceItem(experience_index=3, role="Cashier", company="Grocery Mart", decision="IRRELEVANT", relevant=False, matched_domains=[]),
            CandidateExperienceItem(experience_index=4, role="Rideshare Driver", company="RideCo", decision="IRRELEVANT", relevant=False, matched_domains=[]),
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_08_multi_unrelated_exp.pdf",
            exact_matching=exact_02,
            semantic_retrieval=sem_02,
            experience_matching=exp_08,
        )
    )

    # --------------------------------------------------------------------------
    # SC-09: CAND-09 Overlapping Dates Diagnostic (Jesse Blake)
    # --------------------------------------------------------------------------
    exp_09 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]),
        experience_requirement_present=True,
        relevant_experience_found=True,
        # Concurrent 2-year roles de-duplicated to 2.0 years
        relevant_duration_years=2.0,
        minimum_years=3.0,
        maximum_years=6.0,
        minimum_duration_satisfied=False,  # 2.0 < 3.0 min requirement
        maximum_duration_exceeded=False,
        diagnostic_status="minimum_duration_not_satisfied",
        status="complete",
        experiences=[
            CandidateExperienceItem(experience_index=0, role="Fintech Dev", company="A", decision="RELEVANT", relevant=True, matched_domains=["Fintech"], duration_years=2.0),
            CandidateExperienceItem(experience_index=1, role="Cloud Dev", company="B", decision="RELEVANT", relevant=True, matched_domains=["Cloud Systems"], duration_years=2.0),
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_09_overlapping_dates.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_01,
            experience_matching=exp_09,
        )
    )

    # --------------------------------------------------------------------------
    # SC-10: CAND-10 Missing Dates Diagnostic (Avery Stone)
    # --------------------------------------------------------------------------
    exp_10 = ExperienceMatchingResult(
        experience_requirements=ExperienceRequirementSummary(minimum_years=3.0, maximum_years=6.0, preferred_domains=["Fintech", "Cloud Systems"]),
        experience_requirement_present=True,
        relevant_experience_found=True,
        relevant_duration_years=0.0,
        diagnostic_status="dates_missing_or_unparseable",
        diagnostic_message="Candidate experience dates are missing or invalid.",
        status="complete",
        experiences=[
            CandidateExperienceItem(experience_index=0, role="Fintech Architect", company="A", decision="RELEVANT", relevant=True, matched_domains=["Fintech"], date_status="missing_dates"),
            CandidateExperienceItem(experience_index=1, role="Cloud Architect", company="B", decision="RELEVANT", relevant=True, matched_domains=["Cloud Systems"], date_status="missing_dates"),
        ],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_10_missing_dates.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_01,
            experience_matching=exp_10,
        )
    )

    # --------------------------------------------------------------------------
    # SC-11: CAND-11 LLM Skill Timeout (Logan Frost) -> Incomplete
    # --------------------------------------------------------------------------
    exact_11 = ExactMatchingResult(
        total_required_skills=4,
        matched_required_skills=0,
        unmatched_required_skills=4,
        status="failed",
        error="LLM service connection timeout after 30s",
        matches=[],
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_11_fail_llm_skills.pdf",
            exact_matching=exact_11,
            semantic_retrieval=sem_01,
            experience_matching=exp_01,
        )
    )

    # --------------------------------------------------------------------------
    # SC-12: CAND-12 Retrieval Service Failure (Quinn Harper) -> Incomplete
    # --------------------------------------------------------------------------
    sem_12 = SemanticRetrievalResult(
        status="failed",
        error="Vector embedding retrieval failed: connection refused",
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_12_fail_retrieval.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_12,
            experience_matching=exp_01,
        )
    )

    # --------------------------------------------------------------------------
    # SC-13: Duplicate Candidates A and B for tie-breaking stability
    # --------------------------------------------------------------------------
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_13_duplicate_a.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_01,
            experience_matching=exp_01,
        )
    )
    cohort.append(
        ResumeMatchResult(
            jd_id=jd_id,
            upload_id="batch_eval",
            filename="cand_13_duplicate_b.pdf",
            exact_matching=exact_01,
            semantic_retrieval=sem_01,
            experience_matching=exp_01,
        )
    )

    return cohort
