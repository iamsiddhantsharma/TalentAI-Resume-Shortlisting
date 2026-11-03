from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


BatchStatus = Literal[
    "draft",
    "processing",
    "ready",
    "active",
    "superseded",
    "cancelled",
    "expired",
    "failed",
]


class Batch(BaseModel):
    """
    Represents an isolated recruitment upload batch / session.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    batch_id: str = Field(
        description="Unique identifier for the recruitment batch (corresponds to upload_id).",
    )
    batch_name: str = Field(
        default="Untitled Batch",
        description="Human-readable label or original uploaded file/archive name.",
    )
    status: BatchStatus = Field(
        default="draft",
        description="Current lifecycle state of the batch.",
    )
    is_active: bool = Field(
        default=False,
        description="Whether this batch is the current active candidate batch for matching.",
    )
    total_files: int = Field(
        default=0,
        ge=0,
        description="Total number of discovered candidate files in this batch.",
    )
    processed_count: int = Field(
        default=0,
        ge=0,
        description="Number of candidate files processed so far.",
    )
    completed_count: int = Field(
        default=0,
        ge=0,
        description="Number of candidate files successfully processed.",
    )
    failed_count: int = Field(
        default=0,
        ge=0,
        description="Number of candidate files that failed processing.",
    )
    auto_activate: bool = Field(
        default=False,
        description="Whether the batch should be automatically activated upon successful processing completion.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the batch was created (UTC).",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the batch was last updated (UTC).",
    )
    last_activity_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of most recent activity or processing update (UTC).",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Retention expiry timestamp for inactive/superseded batches. None for active batches.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata or provenance flags (e.g. legacy batch indicator).",
    )


class BatchSummary(BaseModel):
    """
    Summary view of a recruitment batch for list operations.
    """

    batch_id: str
    batch_name: str
    status: BatchStatus
    is_active: bool
    total_files: int
    processed_count: int
    completed_count: int
    failed_count: int
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime | None = None


class BatchListResponse(BaseModel):
    """
    Response model for listing recruitment batches.
    """

    total_batches: int
    active_batch_id: str | None = None
    batches: list[BatchSummary] = Field(default_factory=list)


class BatchActivateResponse(BaseModel):
    """
    Response model for active batch switching.
    """

    status: str = "activated"
    batch_id: str
    previous_active_batch_id: str | None = None
    message: str


class BatchDiscardResponse(BaseModel):
    """
    Response model for discarding or deleting a batch.
    """

    status: str = "discarded"
    batch_id: str
    deleted_resumes_count: int = 0
    deleted_embeddings_count: int = 0
    message: str
