"""
TalentAI — Phase 6: Explainable Ranking Schemas

Defines Pydantic models for transparent score breakdowns, category applicability,
evidence provenance, and batch candidate ranking.
"""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

CategoryApplicability = Literal[
    "applicable",
    "not_applicable",
    "unavailable",
    "complete",
]

CandidateRankingStatus = Literal[
    "complete",
    "incomplete",
    "unranked",
    "no_scorable_requirements",
]


# ==============================================================================
# EVIDENCE DETAIL SCHEMAS
# ==============================================================================


class SkillEvidenceItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    required_skill: str
    matched: bool
    matched_resume_skill: str | None = None
    evidence_type: str | None = None


class SemanticRequirementEvidenceItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    requirement_index: int
    requirement_text: str
    best_matching_passage: str | None = None
    best_matching_section: str | None = None
    raw_similarity: float = 0.0
    normalized_relevance: float = 0.0
    qualifies: bool = False


class ExperienceCriterionEvidenceItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    criterion: str
    best_relevance_score: float = 0.0
    qualifies: bool = False
    supporting_role: str | None = None
    supporting_company: str | None = None
    supporting_decision: str | None = None
    reason: str | None = None
    relevance_ratio: float = 0.0
    calibrated_similarity: float | None = None
    relevant_duration_years: float = 0.0
    relevant_work_summary: str | None = None
    confidence: str | None = None


# ==============================================================================
# CATEGORY SCORE BREAKDOWN SCHEMA
# ==============================================================================


class CategoryScoreBreakdown(BaseModel):
    """
    Transparent, explainable breakdown for an individual scoring category.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: str = Field(description="Name of the scoring category.")
    status: CategoryApplicability = Field(
        description="Applicability and evaluation status of this category for the given JD."
    )
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Calculated category score from 0 to 100, or null if category is not applicable or unavailable.",
    )
    original_weight: float = Field(
        description="Agreed base weight before any JD-specific renormalization."
    )
    normalized_weight: float = Field(
        description="Dynamically renormalized weight based on JD applicability."
    )
    weighted_contribution: float | None = Field(
        default=None,
        description="Score multiplied by normalized weight (normalized_weight * score), or null if uncomputed.",
    )
    total_criteria_count: int = Field(
        default=0,
        description="Total number of JD criteria defined for this category.",
    )
    qualifying_criteria_count: int = Field(
        default=0,
        description="Number of JD criteria that candidate provided qualifying evidence for.",
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Transparent evidence summaries or references linking to extracted candidate evidence.",
    )
    notes: str | None = Field(
        default=None,
        description="Optional diagnostic commentary or reason if category was excluded or failed.",
    )


# ==============================================================================
# CANDIDATE RANKING RESULT SCHEMA
# ==============================================================================


class MinimumExperienceDiagnostic(BaseModel):
    """
    Diagnostic status of minimum and maximum professional experience requirements.
    Separated from the numeric relevance score.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    minimum_years: float | None = None
    maximum_years: float | None = None
    relevant_duration_years: float = 0.0
    minimum_duration_satisfied: bool = True
    maximum_duration_exceeded: bool = False
    diagnostic_status: str | None = None
    diagnostic_message: str | None = None
    duration_factor: float = 0.0
    saturation_target_years: float | None = None
    range_status: str | None = None
    is_range_ambiguous: bool = False


class CandidateRankingResult(BaseModel):
    """
    Complete explainable ranking result for one candidate against the active JD.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    upload_id: str
    filename: str
    jd_id: str
    rank: int | None = Field(
        default=None,
        description="1-indexed rank among completed candidates in the current ranking evaluation.",
    )
    status: CandidateRankingStatus = Field(
        description="Ranking outcome status for this candidate."
    )
    final_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Overall weighted candidate score from 0.0 to 100.0 (rounded to 2 decimal places for display).",
    )
    component_scores: dict[str, float | None] = Field(
        default_factory=dict,
        description="Quick mapping of component name to its 0–100 score.",
    )
    breakdown: dict[str, CategoryScoreBreakdown] = Field(
        default_factory=dict,
        description="Detailed explainable breakdown for each of the four categories.",
    )
    experience_diagnostic: MinimumExperienceDiagnostic = Field(
        default_factory=MinimumExperienceDiagnostic,
        description="Separate diagnostic information regarding experience duration requirements.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Informational diagnostics, e.g. unparseable dates or non-applicable categories.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Technical error messages if any component service failed.",
    )


# ==============================================================================
# API REQUEST & RESPONSE SCHEMAS
# ==============================================================================


class RankResumeRequest(BaseModel):
    """
    Request model for scoring and ranking a single processed resume.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    upload_id: str = Field(
        ...,
        min_length=1,
        description="Upload ID of the resume batch.",
    )
    filename: str = Field(
        ...,
        min_length=1,
        description="Original filename of the processed resume.",
    )
    jd_id: str | None = Field(
        default=None,
        description="Optional JD ID. If omitted, the single active JD is used.",
    )
    use_evidence_based_experience: bool | None = Field(
        default=None,
        description="Optional override for experience scoring engine (True for Evidence-Based, False for Legacy rollback). If omitted, defaults to USE_EVIDENCE_BASED_EXPERIENCE.",
    )


class RankBatchRequest(BaseModel):
    """
    Request model for scoring and ranking all eligible resumes in an active batch.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    upload_id: str | None = Field(
        default=None,
        description="Optional upload ID filter. If omitted, the active batch is used.",
    )
    jd_id: str | None = Field(
        default=None,
        description="Optional JD ID. If omitted, the single active JD is used.",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        description="Optional limit on number of resumes to process in this batch. If omitted or None, all eligible resumes in the batch are ranked.",
    )
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of resumes to skip for pagination.",
    )
    use_evidence_based_experience: bool | None = Field(
        default=None,
        description="Optional override for experience scoring engine (True for Evidence-Based, False for Legacy rollback). If omitted, defaults to USE_EVIDENCE_BASED_EXPERIENCE.",
    )


class BatchRankingResponse(BaseModel):
    """
    Batch ranking response returning candidates ordered by descending final score.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    jd_id: str
    active_batch_id: str | None
    total_eligible: int
    ranked_count: int
    unranked_count: int
    limit: int | None = None
    skip: int = 0
    has_more: bool = False
    ranked_candidates: list[CandidateRankingResult] = Field(
        default_factory=list,
        description="Candidates with complete scoring data, sorted descending by final_score.",
    )
    unranked_candidates: list[CandidateRankingResult] = Field(
        default_factory=list,
        description="Candidates who could not be fully scored due to technical or service failures.",
    )


# ==============================================================================
# ASYNCHRONOUS RANKING JOB SCHEMAS
# ==============================================================================

RankingJobStatus = Literal[
    "queued",
    "processing",
    "completed",
    "failed",
    "interrupted",
]


class RankingJobStatusResponse(BaseModel):
    """
    Response model for asynchronous ranking job status and progress tracking.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    job_id: str = Field(description="Unique identifier for the asynchronous ranking job.")
    status: RankingJobStatus = Field(description="Current status of the ranking job.")
    batch_id: str = Field(description="Active batch identifier associated with this job.")
    jd_id: str = Field(description="Active job description identifier associated with this job.")
    total_eligible: int = Field(
        default=0,
        ge=0,
        description="Total number of eligible completed resumes in the batch.",
    )
    completed_count: int = Field(
        default=0,
        ge=0,
        description="Number of candidates evaluated and scored so far.",
    )
    failed_count: int = Field(
        default=0,
        ge=0,
        description="Number of candidates that failed or could not be fully scored.",
    )
    progress_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Calculated execution progress percentage from 0.0 to 100.0.",
    )
    created_at: str = Field(description="ISO UTC timestamp when the job was created.")
    started_at: str | None = Field(
        default=None,
        description="ISO UTC timestamp when job processing started.",
    )
    finished_at: str | None = Field(
        default=None,
        description="ISO UTC timestamp when job processing finished or terminated.",
    )
    error: str | None = Field(
        default=None,
        description="Concise, sanitized error message if the job failed or was interrupted.",
    )
    result: BatchRankingResponse | None = Field(
        default=None,
        description="Complete BatchRankingResponse payload when status is 'completed'; null otherwise.",
    )

