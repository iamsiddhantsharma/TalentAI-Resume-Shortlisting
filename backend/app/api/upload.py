from fastapi import APIRouter, File, Query, UploadFile

from app.schemas.upload_response import UploadResponse
from app.services.upload_service import upload_service


router = APIRouter(
    prefix="/upload",
    tags=["Resume Upload"],
)


@router.post(
    "/resumes",
    response_model=UploadResponse,
    summary="Upload resumes and create an isolated recruitment batch",
)
async def upload_resumes(
    files: list[UploadFile] = File(...),
    auto_activate: bool = Query(
        default=False,
        description=(
            "If true, automatically sets this batch as the active candidate batch for matching "
            "once processing completes. If false (default), the batch transitions to 'ready' status "
            "and must be explicitly activated via POST /batches/{batch_id}/activate."
        ),
    ),
):
    """
    Upload multiple resume files (ZIP archive, PDF, DOCX, TXT).
    Creates an isolated recruitment batch.
    """

    return await upload_service.create_upload_job(files, auto_activate=auto_activate)
