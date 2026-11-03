from pydantic import BaseModel, Field

from app.schemas.storage import StoredFile


class UploadResponse(BaseModel):
    status: str

    upload_id: str
    batch_id: str | None = None
    batch_status: str | None = None

    total_files_received: int

    supported_files: int

    ignored_files: int

    failed_files: int

    stored_files: list[StoredFile] = Field(
        default_factory=list
    )

    message: str
