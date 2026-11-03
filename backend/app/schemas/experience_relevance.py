from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ExperienceDecision = Literal[
    "RELEVANT",
    "PARTIALLY_RELEVANT",
    "IRRELEVANT",
    "AMBIGUOUS",
    "INSUFFICIENT_INFORMATION",
]


class ExperienceRelevanceDecision(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    experience_index: int = Field(
        description="Zero-based index of the resume experience being evaluated."
    )

    decision: ExperienceDecision = Field(
        description=(
            "Whether the candidate experience is relevant to the "
            "job description experience requirement."
        )
    )

    matched_domains: list[str] = Field(
        default_factory=list,
        description=(
            "Preferred experience domains from the JD that are "
            "supported by this candidate experience."
        )
    )

    matched_context: list[str] = Field(
        default_factory=list,
        description=(
            "JD responsibilities, skills, tools, or work context "
            "that are supported by this experience."
        )
    )

    reason: str = Field(
        default="",
        description=(
            "Short evidence-based explanation for the decision."
        )
    )

    relevant_work_summary: str | None = Field(
        default=None,
        description=(
            "Concise, unembellished candidate excerpt of substantive "
            "domain deliverables, or null if none."
        ),
    )

    relevance_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Relevance multiplier: 1.0 for RELEVANT, 0.5 for PARTIALLY_RELEVANT "
            "(or explicit documented proportion), 0.0 otherwise."
        ),
    )

    evidence_classification: (
        Literal[
            "MODEL_TRAINING_OR_EVAL",
            "INFERENCE_DEPLOYMENT",
            "DATA_PIPELINE",
            "TRANSFERABLE_BACKEND",
            "UNRELATED",
            "UNSPECIFIED",
        ]
        | None
    ) = Field(
        default=None,
        description="Categorization of candidate technical work depth.",
    )

    confidence: Literal["HIGH", "MEDIUM", "LOW"] | None = Field(
        default=None,
        description="Explicit uncertainty tracking for the relevance classification.",
    )


class ExperienceRelevanceResult(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    experience_decisions: list[ExperienceRelevanceDecision] = Field(
        default_factory=list,
        description="Relevance decision for each candidate experience."
    )
