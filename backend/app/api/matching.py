import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.database.batch_repository import batch_repository
from app.database.jd_embedding_repository import jd_embedding_repository
from app.database.jd_repository import jd_repository
from app.database.mongodb import mongodb
from app.database.resume_embedding_repository import resume_embedding_repository
from app.database.resume_repository import resume_repository
from app.schemas.matching import (
    CandidateMatchItem,
    MatchAllRequest,
    MatchAllResponse,
    MatchResumeRequest,
    ResumeMatchResult,
)
from app.services.hybrid_matching_service import hybrid_matching_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/matching",
    tags=["Hybrid Matching"],
)


# ==============================================================================
# POST /matching/match-resume
# ==============================================================================


@router.post(
    "/match-resume",
    response_model=ResumeMatchResult,
    summary="Match one resume against the active job description",
    response_description="Structured matching evidence for the candidate",
)
async def match_resume(
    request: MatchResumeRequest,
) -> ResumeMatchResult:
    """
    Match one existing processed resume against the active Job Description.

    Retrieves:
    1. Active Job Description and its precomputed embeddings.
    2. Stored resume and its precomputed embeddings.
    3. Deterministic exact skills matching against resume skills.
    4. BGE semantic retrieval for responsibilities and tools.
    5. Qwen relevance evaluation and Python duration calculation for experience.

    Returns structured, explainable matching evidence without introducing
    scores, weights, or hiring decisions.
    """

    # --------------------------------------------------------------------------
    # 1. Resolve Active Job Description
    # --------------------------------------------------------------------------

    jd_id = request.jd_id

    if jd_id:
        jd_doc = await jd_repository.get(jd_id)
        if not jd_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job description '{jd_id}' not found.",
            )
    else:
        active_jd = await jd_repository.get_active()
        if not active_jd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No active job description found. "
                    "Please upload a job description before matching."
                ),
            )
        jd_id = active_jd.get("jd_id") or active_jd.get("_id")

    # --------------------------------------------------------------------------
    # 2. Verify Active JD Embeddings Exist
    # --------------------------------------------------------------------------

    jd_emb_doc = await jd_embedding_repository.get_by_jd_id(jd_id)
    if not jd_emb_doc or not jd_emb_doc.get("embeddings"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Embeddings not found for active job description '{jd_id}'. "
                "Please generate JD embeddings."
            ),
        )

    # --------------------------------------------------------------------------
    # 3. Validate Active Batch Ownership
    # --------------------------------------------------------------------------

    active_batch = await batch_repository.get_active()
    if not active_batch:
        hint = ""
        if request.upload_id:
            req_batch = await batch_repository.get(request.upload_id)
            if req_batch:
                b_status = req_batch.get("status")
                hint = (
                    f" Batch '{request.upload_id}' is in status '{b_status}'. "
                    f"Please activate it via POST /batches/{request.upload_id}/activate before matching."
                )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No active recruitment batch found. "
                "Please upload and activate a candidate batch before matching."
                + hint
            ),
        )

    active_batch_id = active_batch.get("batch_id") or active_batch.get("_id")
    if active_batch_id != request.upload_id:
        req_batch = await batch_repository.get(request.upload_id)
        batch_status = req_batch.get("status") if req_batch else "unknown"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Resume '{request.filename}' belongs to batch '{request.upload_id}' "
                f"(status: '{batch_status}'), which is not the active candidate batch. "
                f"Matching is restricted to active batch '{active_batch_id}'."
            ),
        )

    if active_batch.get("status") in ["cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Active batch '{active_batch_id}' has status '{active_batch.get('status')}' and cannot be matched.",
        )

    # --------------------------------------------------------------------------
    # 3. Verify Resume Exists in MongoDB
    # --------------------------------------------------------------------------

    resume_doc = await resume_repository.get(
        upload_id=request.upload_id,
        filename=request.filename,
    )
    if not resume_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Resume not found for upload_id='{request.upload_id}', "
                f"filename='{request.filename}'."
            ),
        )

    if (
        resume_doc.get("status") != "completed"
        or resume_doc.get("resume_data") is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Resume '{request.filename}' is in status "
                f"'{resume_doc.get('status')}' and does not contain valid structured data."
            ),
        )

    # --------------------------------------------------------------------------
    # 4. Verify Resume Embeddings Exist in MongoDB
    # --------------------------------------------------------------------------

    resume_emb_doc = await resume_embedding_repository.get(
        upload_id=request.upload_id,
        filename=request.filename,
    )
    if not resume_emb_doc or not resume_emb_doc.get("embeddings"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Embeddings not found for resume upload_id='{request.upload_id}', "
                f"filename='{request.filename}'."
            ),
        )

    # --------------------------------------------------------------------------
    # 5. Execute Hybrid Matching Orchestration
    # --------------------------------------------------------------------------

    try:
        raw_result = await hybrid_matching_service.match_resume(
            jd_id=jd_id,
            upload_id=request.upload_id,
            filename=request.filename,
        )
        return ResumeMatchResult.model_validate(raw_result)

    except ValueError as exc:
        logger.warning(
            "Validation error during matching for %s:%s - %s",
            request.upload_id,
            request.filename,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception(
            "Unexpected error during matching for %s:%s",
            request.upload_id,
            request.filename,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Matching failed due to an unexpected server error.",
        )


# ==============================================================================
# POST /matching/match-all
# ==============================================================================


@router.post(
    "/match-all",
    response_model=MatchAllResponse,
    summary="Match all eligible resumes against the single active job description",
    response_description="Batch matching results with per-candidate status and counts",
)
async def match_all(
    request: MatchAllRequest = MatchAllRequest(),
) -> MatchAllResponse:
    """
    Match all eligible stored resumes against the single active Job Description.

    Requirements & Constraints:
    - Verifies the active JD and its embeddings exist (returns 404 if missing).
    - Queries eligible completed resumes from MongoDB.
    - Applies pagination / bounded batch limits (default 50, max 100) to protect system resources.
    - Matches each candidate independently.
    - Captures per-candidate success/failure without failing the entire batch or leaking internal stack traces.
    - Returns summary counts (processed, successful, failed).
    """

    # --------------------------------------------------------------------------
    # 1. Resolve Active Job Description
    # --------------------------------------------------------------------------

    jd_id = request.jd_id

    if jd_id:
        jd_doc = await jd_repository.get(jd_id)
        if not jd_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job description '{jd_id}' not found.",
            )
    else:
        active_jd = await jd_repository.get_active()
        if not active_jd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No active job description found. "
                    "Please upload a job description before matching."
                ),
            )
        jd_id = active_jd.get("jd_id") or active_jd.get("_id")

    # --------------------------------------------------------------------------
    # 2. Verify Active JD Embeddings Exist
    # --------------------------------------------------------------------------

    jd_emb_doc = await jd_embedding_repository.get_by_jd_id(jd_id)
    if not jd_emb_doc or not jd_emb_doc.get("embeddings"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Embeddings not found for active job description '{jd_id}'. "
                "Please generate JD embeddings."
            ),
        )

    # --------------------------------------------------------------------------
    # 3. Resolve and Validate Active Batch
    # --------------------------------------------------------------------------

    active_batch = await batch_repository.get_active()
    if not active_batch:
        hint = ""
        if request.upload_id:
            req_batch = await batch_repository.get(request.upload_id)
            if req_batch:
                b_status = req_batch.get("status")
                hint = (
                    f" Batch '{request.upload_id}' is in status '{b_status}'. "
                    f"Please activate it via POST /batches/{request.upload_id}/activate before matching."
                )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No active recruitment batch found. "
                "Please upload and activate a candidate batch before matching."
                + hint
            ),
        )

    active_batch_id = active_batch.get("batch_id") or active_batch.get("_id")
    if request.upload_id:
        if request.upload_id != active_batch_id:
            req_batch = await batch_repository.get(request.upload_id)
            batch_status = req_batch.get("status") if req_batch else "unknown"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Specified batch '{request.upload_id}' (status: '{batch_status}') "
                    f"is not the active candidate batch. "
                    f"Matching is restricted to active batch '{active_batch_id}'."
                ),
            )
        target_upload_id = request.upload_id
    else:
        target_upload_id = active_batch_id

    if active_batch.get("status") in ["cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Active batch '{active_batch_id}' has status '{active_batch.get('status')}' and cannot be matched.",
        )

    # --------------------------------------------------------------------------
    # 4. Query Eligible Resumes Strictly from Active Batch in MongoDB
    # --------------------------------------------------------------------------

    db = mongodb.get_database()
    resumes_collection = db.get("resumes") if isinstance(db, dict) else db["resumes"]

    query: dict[str, Any] = {
        "upload_id": target_upload_id,
        "status": "completed",
        "resume_data": {"$ne": None},
    }

    total_eligible = await resumes_collection.count_documents(query)

    cursor = (
        resumes_collection.find(
            query,
            projection={"upload_id": 1, "filename": 1},
        )
        .skip(request.skip)
        .limit(request.limit)
    )
    eligible_docs = await cursor.to_list(length=request.limit)

    has_more = (request.skip + len(eligible_docs)) < total_eligible

    # --------------------------------------------------------------------------
    # 4. Process Each Candidate Independently
    # --------------------------------------------------------------------------

    results: list[CandidateMatchItem] = []
    successful_count = 0
    failed_count = 0

    for doc in eligible_docs:
        upload_id = doc.get("upload_id")
        filename = doc.get("filename")

        if not upload_id or not filename:
            continue

        # Check if embeddings exist for this resume
        resume_emb_doc = await resume_embedding_repository.get(
            upload_id=upload_id,
            filename=filename,
        )

        if not resume_emb_doc or not resume_emb_doc.get("embeddings"):
            failed_count += 1
            results.append(
                CandidateMatchItem(
                    upload_id=upload_id,
                    filename=filename,
                    status="failed",
                    error="Embeddings not found for resume. Ingestion embedding generation may have failed.",
                    match=None,
                )
            )
            continue

        # Match resume against the active JD
        try:
            raw_match = await hybrid_matching_service.match_resume(
                jd_id=jd_id,
                upload_id=upload_id,
                filename=filename,
            )
            validated_match = ResumeMatchResult.model_validate(raw_match)
            successful_count += 1
            results.append(
                CandidateMatchItem(
                    upload_id=upload_id,
                    filename=filename,
                    status="completed",
                    error=None,
                    match=validated_match,
                )
            )

        except Exception as exc:
            logger.exception(
                "Batch matching failure for candidate %s:%s",
                upload_id,
                filename,
            )
            failed_count += 1
            results.append(
                CandidateMatchItem(
                    upload_id=upload_id,
                    filename=filename,
                    status="failed",
                    error=str(exc),
                    match=None,
                )
            )

    return MatchAllResponse(
        jd_id=jd_id,
        total_eligible_resumes=total_eligible,
        processed_count=len(eligible_docs),
        successful_count=successful_count,
        failed_count=failed_count,
        limit=request.limit,
        skip=request.skip,
        has_more=has_more,
        results=results,
    )
