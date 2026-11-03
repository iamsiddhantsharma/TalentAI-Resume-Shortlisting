from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExperienceRequirement(BaseModel):
    """
    Structured experience requirement for a job.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    minimum_years: float | None = Field(
        default=None,
        description="Minimum years of overall professional experience required.",
    )

    maximum_years: float | None = Field(
        default=None,
        description="Maximum years of overall professional experience mentioned.",
    )

    preferred_domains: list[str] = Field(
        default_factory=list,
        description="Industries or professional domains explicitly preferred.",
    )


class JobDescriptionObject(BaseModel):
    """
    Minimal structured representation of a Job Description
    for TalentAI matching.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    required_skills: list[str] = Field(
        default_factory=list,
        description="Skills explicitly required or expected for the role.",
    )

    responsibilities: list[str] = Field(
        default_factory=list,
        description="Major responsibilities and work activities of the role.",
    )

    experience_requirements: list[ExperienceRequirement] = Field(
        default_factory=list,
        description="Overall professional experience requirements.",
    )

    tools_and_technologies: list[str] = Field(
        default_factory=list,
        description="Tools, technologies, platforms, frameworks, and software explicitly mentioned.",
    )

    @field_validator("required_skills", "tools_and_technologies", mode="before")
    @classmethod
    def clean_and_deduplicate(cls, items: object) -> list[str]:
        """
        Deduplicate skills and tools case-insensitively while
        preserving first occurrence order and casing. Filters out None
        and empty whitespace strings.
        """
        if not isinstance(items, list):
            return items  # type: ignore

        seen: set[str] = set()
        cleaned: list[str] = []
        for item in items:
            if not item or not isinstance(item, str):
                continue
            trimmed = item.strip()
            if trimmed and trimmed.lower() not in seen:
                seen.add(trimmed.lower())
                cleaned.append(trimmed)
        return cleaned
