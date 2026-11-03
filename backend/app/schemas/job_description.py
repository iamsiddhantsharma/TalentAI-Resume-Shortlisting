from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.job_description_object import (
    JobDescriptionObject,
)


class JobDescription(BaseModel):
    """
    Final Job Description response returned by
    the Job Description API.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    jd_id: str = Field(
        description="Unique ID of the Job Description."
    )

    input_type: Literal[
        "file",
        "text",
    ] = Field(
        description="How the Job Description was provided."
    )

    filename: str | None = Field(
        default=None,
        description="Original uploaded filename.",
    )

    file_extension: str | None = Field(
        default=None,
        description="Normalized file extension.",
    )

    raw_text: str = Field(
        description="Normalized Job Description text.",
    )

    status: Literal[
        "parsed",
        "completed",
        "failed",
    ] = Field(
        description="Current JD processing status.",
    )

    structured_data: JobDescriptionObject | None = Field(
        default=None,
        description=(
            "Extracted Job Description data containing "
            "required skills and overall experience."
        ),
    )

    error: str | None = Field(
        default=None,
        description="Processing error if any.",
    )
