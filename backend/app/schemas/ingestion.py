from pydantic import BaseModel, ConfigDict, Field

from app.schemas.discovered_file import DiscoveredFile


class ResumeIngestionItem(BaseModel):
    """
    Represents one resume that has entered the TalentAI
    processing pipeline.

    This object carries the discovered file together with
    its processing identity.

    No resume text or AI-generated information is stored here.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    ingestion_id: str = Field(
        description="Unique ID for this resume processing item."
    )

    upload_id: str = Field(
        description="ID of the original upload request."
    )

    file: DiscoveredFile = Field(
        description="Discovered resume and its provenance."
    )

    status: str = Field(
        default="queued",
        description="Current processing status."
    )
