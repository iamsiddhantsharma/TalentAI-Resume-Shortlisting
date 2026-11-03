from pydantic import BaseModel, ConfigDict, Field


class ProcessingJob(BaseModel):
    """
    Represents one resume waiting to be processed.

    This object carries the resume location as well as
    folder provenance information.
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
        description="Path to the resume file."
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
        description="Folder depth of the resume."
    )

    is_root_level: bool = Field(
        default=True,
        description="Whether the resume is at root level."
    )
