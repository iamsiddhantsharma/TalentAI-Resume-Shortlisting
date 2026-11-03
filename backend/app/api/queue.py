from fastapi import APIRouter, Depends

from app.auth.auth_dependencies import get_current_hr_user
from app.queue.local_queue import local_queue


router = APIRouter(
    prefix="/queue",
    tags=["Processing Queue"],
    dependencies=[Depends(get_current_hr_user)],
)


@router.get("/status")
async def get_queue_status() -> dict:
    """
    Return the current status of the resume processing queue.

    This endpoint is intended for monitoring and development.
    """

    queue_size = local_queue.size()

    return {
        "queue_size": queue_size,
        "status": (
            "processing_pending"
            if queue_size > 0
            else "queue_empty"
        ),
    }
