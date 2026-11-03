from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# REQUEST SCHEMAS
# ==============================================================================


class MatchResumeRequest(BaseModel):
    """
    Request model for matching a single processed resume against the active JD.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

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


class MatchAllRequest(BaseModel):
    """
    Request model for matching all eligible resumes against the active JD.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    jd_id: str | None = Field(
        default=None,
        description="Optional JD ID. If omitted, the single active JD is used.",
    )
    upload_id: str | None = Field(
        default=None,
        description="Optional upload ID filter to match resumes only from a specific upload batch.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of resumes to process in this batch (bounded to prevent resource exhaustion).",
    )
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of eligible resumes to skip for pagination.",
    )


# ==============================================================================
# EXACT MATCHING EVIDENCE SCHEMAS
# ==============================================================================


class ExactSkillMatchItem(BaseModel):
    required_skill: str
    matched: bool
    resume_skill: str | None = None
    match_type: str | None = None
    similarity: float | None = None
    retrieved_skill: str | None = None


class ExactMatchingResult(BaseModel):
    total_required_skills: int
    matched_required_skills: int
    unmatched_required_skills: int
    matches: list[ExactSkillMatchItem] = Field(default_factory=list)
    status: str | None = None
    error: str | None = None


# ==============================================================================
# SEMANTIC RETRIEVAL EVIDENCE SCHEMAS
# ==============================================================================


class SemanticEvidenceMatchItem(BaseModel):
    jd_section: str | None = None
    jd_item_index: int | None = None
    jd_text: str | None = None
    resume_section: str | None = None
    resume_item_index: int | None = None
    resume_text: str | None = None
    similarity: float


class SemanticRetrievalRequirementResult(BaseModel):
    jd_section: str | None = None
    jd_item_index: int | None = None
    jd_text: str | None = None
    matches: list[SemanticEvidenceMatchItem] = Field(default_factory=list)


class SemanticSectionRetrieval(BaseModel):
    top_k: int = 5
    results: list[SemanticRetrievalRequirementResult] = Field(
        default_factory=list
    )
    status: str | None = None
    error: str | None = None


class SemanticRetrievalResult(BaseModel):
    top_k: int = 5
    responsibilities_retrieval: SemanticSectionRetrieval | None = None
    tools_and_technologies_retrieval: SemanticSectionRetrieval | None = None
    results: list[SemanticRetrievalRequirementResult] = Field(
        default_factory=list
    )
    status: str | None = None
    error: str | None = None


# ==============================================================================
# EXPERIENCE MATCHING EVIDENCE SCHEMAS
# ==============================================================================


class ExperienceRequirementSummary(BaseModel):
    minimum_years: float | None = None
    maximum_years: float | None = None
    preferred_domains: list[str] = Field(default_factory=list)


class CandidateExperienceItem(BaseModel):
    experience_index: int
    role: str | None = None
    company: str | None = None
    description: str | None = None
    decision: str | None = None
    relevant: bool
    matched_domains: list[str] = Field(default_factory=list)
    duration_years: float = 0.0
    duration_available: bool = False
    start_date: str | None = None
    end_date: str | None = None
    date_status: str | None = None
    relevance_ratio: float = 0.0
    relevant_duration_years: float = 0.0
    semantic_similarity: float | None = None
    calibrated_similarity: float | None = None
    relevant_work_summary: str | None = None
    confidence: str | None = None


class ExperienceMatchingResult(BaseModel):
    experience_requirements: ExperienceRequirementSummary = Field(
        default_factory=ExperienceRequirementSummary
    )
    experience_requirement_present: bool = False
    experiences: list[CandidateExperienceItem] = Field(default_factory=list)
    relevant_experience_found: bool = False
    relevant_duration_years: float = 0.0
    minimum_years: float | None = None
    maximum_years: float | None = None
    minimum_duration_satisfied: bool = False
    maximum_duration_exceeded: bool = False
    diagnostic_status: str | None = None
    diagnostic_message: str | None = None
    status: str | None = None
    error: str | None = None
    duration_factor: float = 0.0
    aggregated_similarity: float = 0.0
    experience_score: float = 0.0
    range_status: str | None = None
    saturation_target_years: float | None = None


# ==============================================================================
# COMBINED MATCHING RESPONSE SCHEMAS
# ==============================================================================


class ResumeMatchResult(BaseModel):
    """
    Detailed, explainable matching evidence for one resume against one JD.

    Contains raw matching signals only. Does NOT contain scores, weights,
    rankings, or hiring decisions.
    """

    jd_id: str
    upload_id: str
    filename: str
    exact_matching: ExactMatchingResult
    semantic_retrieval: SemanticRetrievalResult
    experience_matching: ExperienceMatchingResult


class CandidateMatchItem(BaseModel):
    """
    Individual candidate matching result in a batch operation.
    """

    upload_id: str
    filename: str
    status: Literal["completed", "failed"]
    error: str | None = None
    match: ResumeMatchResult | None = None


class MatchAllResponse(BaseModel):
    """
    Batch matching response summarizing processing across eligible resumes.
    """

    jd_id: str
    total_eligible_resumes: int
    processed_count: int
    successful_count: int
    failed_count: int
    limit: int
    skip: int
    has_more: bool
    results: list[CandidateMatchItem] = Field(default_factory=list)
