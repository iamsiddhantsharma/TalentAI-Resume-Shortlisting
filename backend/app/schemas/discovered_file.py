from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DiscoveredFile(BaseModel):
    """
    Represents a resume file discovered inside an extracted
    directory structure.

    This model contains file-system and ZIP provenance
    information only. Resume content is handled later
    by the Resume Parser.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    # --------------------------------------------------
    # File information
    # --------------------------------------------------

    filename: str = Field(
        description="Original filename of the discovered file."
    )

    file_path: str = Field(
        description="Absolute or application-resolved path to the file."
    )

    relative_path: str = Field(
        description=(
            "Path relative to the extraction root, "
            "preserving the complete directory hierarchy."
        )
    )

    file_extension: str = Field(
        description="Normalized file extension, such as .pdf."
    )

    # --------------------------------------------------
    # Folder provenance
    # --------------------------------------------------

    source_folder: str | None = Field(
        default=None,
        description=(
            "Complete relative folder path containing the file. "
            "None when the file is directly inside the extraction root."
        )
    )

    folder_chain: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of folders from extraction root "
            "to the file's immediate parent directory."
        )
    )

    folder_depth: int = Field(
        default=0,
        ge=0,
        description="Number of directory levels between root and file."
    )

    is_root_level: bool = Field(
        default=True,
        description="True when the file is directly inside the extraction root."
    )
