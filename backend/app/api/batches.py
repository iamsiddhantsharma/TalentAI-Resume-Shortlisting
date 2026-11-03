import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.database.batch_repository import batch_repository
from app.schemas.batch import (
    BatchActivateResponse,
    BatchDiscardResponse,
    BatchListResponse,
    BatchSummary,
)
from app.services.retention_service import retention_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/batches",
    tags=["Recruitment Batches"],
)


@router.get(
    "",
    response_model=BatchListResponse,
    summary="List all recruitment batches",
)
async def list_batches(
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> BatchListResponse:
    """
    List all recruitment batches ordered by creation date descending.
    """
    batch_docs = await batch_repository.list_batches(limit=limit, skip=skip)
    active_batch = await batch_repository.get_active()
    active_id = active_batch.get("batch_id") or active_batch.get("_id") if active_batch else None
    total_count = await batch_repository.count()

    summaries = []
    for b in batch_docs:
        summaries.append(
            BatchSummary(
                batch_id=b.get("batch_id") or b.get("_id"),
                batch_name=b.get("batch_name", "Untitled"),
                status=b.get("status", "draft"),
                is_active=b.get("is_active", False),
                total_files=b.get("total_files", 0),
                processed_count=b.get("processed_count", 0),
                completed_count=b.get("completed_count", 0),
                failed_count=b.get("failed_count", 0),
                created_at=b.get("created_at"),
                last_activity_at=b.get("last_activity_at"),
                expires_at=b.get("expires_at"),
            )
        )

    return BatchListResponse(
        total_batches=total_count,
        active_batch_id=active_id,
        batches=summaries,
    )


@router.get(
    "/active",
    summary="Get the currently active recruitment batch",
)
async def get_active_batch() -> dict[str, Any]:
    """
    Retrieve the current active recruitment batch used for matching.
    """
    active_batch = await batch_repository.get_active()
    if not active_batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active recruitment batch found.",
        )
    return active_batch


@router.get(
    "/{batch_id}",
    summary="Get details for one recruitment batch",
)
async def get_batch(batch_id: str) -> dict[str, Any]:
    """
    Retrieve status and candidate processing metrics for a specific batch.
    """
    batch_doc = await batch_repository.get(batch_id)
    if not batch_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found.",
        )
    return batch_doc


@router.post(
    "/{batch_id}/activate",
    response_model=BatchActivateResponse,
    summary="Set a batch as the active candidate batch",
)
async def activate_batch(batch_id: str) -> BatchActivateResponse:
    """
    Atomically switch the active recruitment batch.
    The previous active batch is superseded and matching uses only this new batch.
    """
    current_active = await batch_repository.get_active()
    prev_id = (
        current_active.get("batch_id") or current_active.get("_id")
        if current_active
        else None
    )

    try:
        updated = await batch_repository.activate(batch_id)
        return BatchActivateResponse(
            status="activated",
            batch_id=batch_id,
            previous_active_batch_id=prev_id,
            message=f"Batch '{batch_id}' is now the active candidate batch.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Failed to activate batch %s", batch_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error activating batch.",
        )


@router.delete(
    "/{batch_id}",
    response_model=BatchDiscardResponse,
    summary="Discard/delete a recruitment batch",
)
@router.post(
    "/{batch_id}/discard",
    response_model=BatchDiscardResponse,
    summary="Discard/delete a recruitment batch",
)
async def discard_batch(
    batch_id: str,
    force: bool = Query(default=False, description="Force discard even if active"),
) -> BatchDiscardResponse:
    """
    Permanently discard a batch, deleting its resumes, embeddings, and files.
    Active batches require force=True.
    """
    try:
        res = await retention_service.discard_batch(batch_id=batch_id, force=force)
        return BatchDiscardResponse(
            status="discarded",
            batch_id=batch_id,
            deleted_resumes_count=res["resumes_deleted"],
            deleted_embeddings_count=res["embeddings_deleted"],
            message=f"Batch '{batch_id}' and all associated candidate data were deleted.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Failed to discard batch %s", batch_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error discarding batch.",
        )


@router.post(
    "/cleanup-expired",
    summary="Manually trigger expired batch cleanup",
)
async def trigger_cleanup_expired() -> dict[str, Any]:
    """
    Manually trigger cleanup of expired inactive batches.
    """
    cleaned = await retention_service.cleanup_expired_batches()
    return {
        "status": "completed",
        "expired_batches_cleaned": cleaned,
    }
