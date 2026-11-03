from pydantic import BaseModel, ConfigDict, Field


class Education(BaseModel):
    """
    Structured education information extracted from a resume.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    degree: str | None = Field(
        default=None,
        description="Degree or qualification.",
    )

    field_of_study: str | None = Field(
        default=None,
        description="Field or specialization.",
    )

    institution: str | None = Field(
        default=None,
        description="Name of the educational institution.",
    )

    start_year: int | None = Field(
        default=None,
        description="Starting year.",
    )

    end_year: int | None = Field(
        default=None,
        description="Completion or expected completion year.",
    )

    grade: str | None = Field(
        default=None,
        description="CGPA, percentage, GPA, or other grade.",
    )


class Experience(BaseModel):
    """
    Structured work experience extracted from a resume.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    company: str | None = Field(
        default=None,
        description="Company or organization name.",
    )

    role: str | None = Field(
        default=None,
        description="Job title or role.",
    )

    start_date: str | None = Field(
        default=None,
        description="Employment start date.",
    )

    end_date: str | None = Field(
        default=None,
        description="Employment end date.",
    )

    description: str | None = Field(
        default=None,
        description="Description of responsibilities and work.",
    )


class Project(BaseModel):
    """
    Structured project information extracted from a resume.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    name: str | None = Field(
        default=None,
        description="Project name.",
    )

    description: str | None = Field(
        default=None,
        description="Complete project description.",
    )

    technologies: list[str] = Field(
        default_factory=list,
        description="Technologies and tools used.",
    )


class Certification(BaseModel):
    """
    Structured certification information extracted from a resume.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    name: str | None = Field(
        default=None,
        description="Certification name.",
    )

    issuing_organization: str | None = Field(
        default=None,
        description="Organization that issued the certification.",
    )

    year: int | None = Field(
        default=None,
        description="Certification year.",
    )


class CodingProfile(BaseModel):
    """
    Coding or professional profile containing
    the platform name and the actual profile URL.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    platform: str = Field(
        description=(
            "Platform name such as LinkedIn, "
            "GitHub, LeetCode, HackerRank, CodeChef, etc."
        ),
    )

    url: str = Field(
        description="Actual profile URL found in the resume.",
    )


class ResumeObject(BaseModel):
    """
    Structured representation of a resume.

    This model is the canonical schema used by TalentAI
    for LLM-generated resume information.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    # ---------------------------------------------
    # Personal information
    # ---------------------------------------------

    name: str | None = Field(
        default=None,
        description="Candidate's full name.",
    )

    email: str | None = Field(
        default=None,
        description="Candidate's email address.",
    )

    phone: str | None = Field(
        default=None,
        description="Candidate's phone number.",
    )

    location: str | None = Field(
        default=None,
        description="Candidate's location.",
    )

    # ---------------------------------------------
    # Professional information
    # ---------------------------------------------

    summary: str | None = Field(
        default=None,
        description="Professional summary.",
    )

    skills: list[str] = Field(
        default_factory=list,
        description="Technical and professional skills.",
    )

    # ---------------------------------------------
    # Structured sections
    # ---------------------------------------------

    education: list[Education] = Field(
        default_factory=list,
        description="Educational qualifications.",
    )

    experience: list[Experience] = Field(
        default_factory=list,
        description="Professional work experience.",
    )

    projects: list[Project] = Field(
        default_factory=list,
        description="Projects completed by the candidate.",
    )

    certifications: list[Certification] = Field(
        default_factory=list,
        description="Professional certifications.",
    )

    achievements: list[str] = Field(
        default_factory=list,
        description="Awards and achievements.",
    )

    interests: list[str] = Field(
        default_factory=list,
        description="Professional or personal interests.",
    )

    coding_profiles: list[CodingProfile] = Field(
        default_factory=list,
        description=(
            "Coding, professional, portfolio, and social "
            "profiles with their actual URLs."
        ),
    )
