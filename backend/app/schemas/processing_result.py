from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.resume_object import ResumeObject


class ProcessingResult(BaseModel):
    """
    Represents the final processing result of one resume.

    This object preserves:
    - normalized resume text
    - structured LLM-extracted resume information
    - original folder provenance
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    upload_id: str = Field(
        description="ID of the upload request."
    )

    filename: str = Field(
        description="Original resume filename."
    )

    file_path: str = Field(
        description="Path of the resume file."
    )

    file_extension: str = Field(
        description="Normalized file extension."
    )

    relative_path: str = Field(
        description="Path relative to the extraction root."
    )

    source_folder: str | None = Field(
        default=None,
        description="Folder containing the resume."
    )

    folder_chain: list[str] = Field(
        default_factory=list,
        description="Complete folder hierarchy."
    )

    folder_depth: int = Field(
        default=0,
        ge=0,
        description="Number of folder levels."
    )

    is_root_level: bool = Field(
        default=True,
        description="Whether the resume is at extraction root."
    )

    status: Literal[
        "completed",
        "failed",
    ] = Field(
        description="Processing status."
    )

    text: str | None = Field(
        default=None,
        description="Normalized resume text."
    )

    resume_data: ResumeObject | None = Field(
        default=None,
        description=(
            "Structured resume information extracted "
            "by the LLM and validated by Pydantic."
        ),
    )

    error: str | None = Field(
        default=None,
        description="Processing error if processing failed."
    )
