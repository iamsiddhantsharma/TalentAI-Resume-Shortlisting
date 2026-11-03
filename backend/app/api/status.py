from fastapi import APIRouter

from app.database.batch_repository import batch_repository
from app.queue.local_queue import local_queue
from app.services.ai_lifecycle_manager import ai_lifecycle_manager
from app.services.result_store import result_store


router = APIRouter(
    prefix="/status",
    tags=["System Status"],
)


@router.get("/ai-model")
async def ai_model_status():
    """
    Return the operational status of the on-demand Ollama AI lifecycle manager.
    """
    return ai_lifecycle_manager.get_status()


@router.get("/")
async def status():
    """
    Basic application status.
    """

    return {
        "status": "running",
        "queue_size": local_queue.size(),
    }


@router.get("/queue")
async def queue_status():
    """
    Return the current number of queued jobs.
    """

    return {
        "queue_size": local_queue.size(),
    }


@router.get("/upload/{upload_id}")
async def upload_status(
    upload_id: str,
):
    """
    Return processing status and results for one upload.

    This endpoint allows the frontend/Swagger UI to see:
    - total files
    - completed files
    - failed files
    - currently processing files
    - individual processing results
    """

    results = result_store.get_by_upload(
        upload_id
    )

    completed = sum(
        1
        for result in results
        if result.status == "completed"
    )

    failed = sum(
        1
        for result in results
        if result.status == "failed"
    )

    processing = max(
        0,
        local_queue.size(),
    )

    total = len(results) + processing

    batch = await batch_repository.get(upload_id)
    batch_status = batch.get("status") if batch else None
    is_active = batch.get("is_active", False) if batch else False

    return {
        "upload_id": upload_id,
        "batch_id": upload_id,
        "batch_status": batch_status,
        "is_active": is_active,
        "total": total,
        "completed": completed,
        "failed": failed,
        "processing": processing,
        "results": [
            {
                "filename": result.filename,
                "file_path": result.file_path,
                "file_extension": result.file_extension,
                "relative_path": result.relative_path,
                "source_folder": result.source_folder,
                "folder_chain": result.folder_chain,
                "folder_depth": result.folder_depth,
                "is_root_level": result.is_root_level,
                "status": result.status,
                "text": result.text,
                "error": result.error,
            }
            for result in results
        ],
    }
