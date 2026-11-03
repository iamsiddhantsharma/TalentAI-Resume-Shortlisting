"""
TalentAI — Phase 6: Ranking Engine API Router

Endpoints for calculating explainable candidate scores and ranking candidates
against the single active Job Description.
"""

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status

from app.database.batch_repository import batch_repository
from app.database.jd_embedding_repository import jd_embedding_repository
from app.database.jd_repository import jd_repository
from app.database.ranking_job_repository import ranking_job_repository
from app.database.resume_embedding_repository import resume_embedding_repository
from app.database.resume_repository import resume_repository
from app.ranking.ranking_schemas import (
    BatchRankingResponse,
    CandidateRankingResult,
    RankBatchRequest,
    RankResumeRequest,
    RankingJobStatusResponse,
)
from app.ranking.ranking_service import ranking_engine
from app.schemas.job_description import JobDescription
from app.schemas.matching import ResumeMatchResult

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ranking",
    tags=["Explainable Ranking Engine"],
)


# ==============================================================================
# POST /ranking/rank-resume
# ==============================================================================


@router.post(
    "/rank-resume",
    response_model=CandidateRankingResult,
    summary="Rank and score one resume against the active job description",
    response_description="Transparent component scores, weights, and overall candidate ranking",
)
async def rank_resume(
    request: RankResumeRequest,
) -> CandidateRankingResult:
    """
    Score and explain a single processed resume against the active Job Description.

    Enforces:
    1. Active Job Description and precomputed embeddings existence check.
    2. Active batch ownership and isolation validation.
    3. Resume existence and status validation.
    4. Deterministic component scoring across the 4 categories.
    5. Proportional weight renormalization based on JD applicability.
    6. Minimum experience duration diagnostic reporting.
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
                detail="No active job description found. Please upload a job description before ranking.",
            )
        jd_id = active_jd.get("jd_id") or active_jd.get("_id")
        jd_doc = active_jd

    raw_struct = jd_doc.get("structured_data")
    if not raw_struct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job description '{jd_id}' does not contain structured data.",
        )

    # --------------------------------------------------------------------------
    # 2. Verify Active JD Embeddings Exist
    # --------------------------------------------------------------------------
    jd_emb_doc = await jd_embedding_repository.get_by_jd_id(jd_id)
    if not jd_emb_doc or not jd_emb_doc.get("embeddings"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Embeddings not found for active job description '{jd_id}'. Please generate JD embeddings.",
        )

    # --------------------------------------------------------------------------
    # 3. Validate Active Batch Ownership & Status
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
                    f"Please activate it via POST /batches/{request.upload_id}/activate before ranking."
                )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active recruitment batch found. Please upload and activate a candidate batch before ranking." + hint,
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
                f"Ranking is restricted to active batch '{active_batch_id}'."
            ),
        )

    if active_batch.get("status") in ["cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Active batch '{active_batch_id}' has status '{active_batch.get('status')}' and cannot be ranked.",
        )

    # --------------------------------------------------------------------------
    # 4. Verify Resume and Resume Embeddings Exist in MongoDB
    # --------------------------------------------------------------------------
    resume_doc = await resume_repository.get(
        upload_id=request.upload_id,
        filename=request.filename,
    )
    if not resume_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume not found for upload_id='{request.upload_id}', filename='{request.filename}'.",
        )

    if resume_doc.get("status") != "completed" or resume_doc.get("resume_data") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resume '{request.filename}' is in status '{resume_doc.get('status')}' and does not contain valid structured data.",
        )

    resume_emb_doc = await resume_embedding_repository.get(
        upload_id=request.upload_id,
        filename=request.filename,
    )
    if not resume_emb_doc or not resume_emb_doc.get("embeddings"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Embeddings not found for resume upload_id='{request.upload_id}', filename='{request.filename}'.",
        )

    # --------------------------------------------------------------------------
    # 5. Execute Ranking Calculation
    # --------------------------------------------------------------------------
    try:
        ranking_result = await ranking_engine.rank_resume(
            upload_id=request.upload_id,
            filename=request.filename,
            jd_id=jd_id,
            use_evidence_based_experience=request.use_evidence_based_experience,
        )
        return ranking_result

    except ValueError as exc:
        logger.warning("Validation error during ranking for %s:%s - %s", request.upload_id, request.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error during ranking for %s:%s", request.upload_id, request.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ranking calculation failed due to an unexpected server error.",
        )


# ==============================================================================
# POST /ranking/rank-batch
# ==============================================================================


@router.post(
    "/rank-batch",
    response_model=BatchRankingResponse,
    summary="Rank all eligible resumes from active batch against active job description",
    response_description="Ordered list of candidates ranked descending by final score with explainable breakdown",
)
async def rank_batch(
    request: RankBatchRequest = RankBatchRequest(),
) -> BatchRankingResponse:
    """
    Score and rank all eligible completed resumes from the active batch against the active Job Description.

    Returns:
    - Ranked candidates sorted descending by overall score.
    - Unranked candidates separated transparently if technical service failures occurred.
    - Comprehensive metadata and pagination support.
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
                detail="No active job description found. Please upload a job description before ranking.",
            )
        jd_id = active_jd.get("jd_id") or active_jd.get("_id")

    # --------------------------------------------------------------------------
    # 2. Verify Active JD Embeddings Exist
    # --------------------------------------------------------------------------
    jd_emb_doc = await jd_embedding_repository.get_by_jd_id(jd_id)
    if not jd_emb_doc or not jd_emb_doc.get("embeddings"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Embeddings not found for active job description '{jd_id}'. Please generate JD embeddings.",
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
                    f"Please activate it via POST /batches/{request.upload_id}/activate before ranking."
                )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active recruitment batch found. Please upload and activate a candidate batch before ranking." + hint,
        )

    active_batch_id = active_batch.get("batch_id") or active_batch.get("_id")
    if request.upload_id and request.upload_id != active_batch_id:
        req_batch = await batch_repository.get(request.upload_id)
        batch_status = req_batch.get("status") if req_batch else "unknown"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Specified batch '{request.upload_id}' (status: '{batch_status}') "
                f"is not the active candidate batch. "
                f"Ranking is restricted to active batch '{active_batch_id}'."
            ),
        )

    if active_batch.get("status") in ["cancelled", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Active batch '{active_batch_id}' has status '{active_batch.get('status')}' and cannot be ranked.",
        )

    # --------------------------------------------------------------------------
    # 4. Execute Batch Ranking
    # --------------------------------------------------------------------------
    try:
        resolved_jd_id, target_batch_id, total_eligible, ranked, unranked, has_more = (
            await ranking_engine.rank_batch(
                upload_id=request.upload_id,
                jd_id=jd_id,
                limit=request.limit,
                skip=request.skip,
                use_evidence_based_experience=request.use_evidence_based_experience,
            )
        )

        return BatchRankingResponse(
            jd_id=resolved_jd_id,
            active_batch_id=target_batch_id,
            total_eligible=total_eligible,
            ranked_count=len(ranked),
            unranked_count=len(unranked),
            limit=request.limit,
            skip=request.skip,
            has_more=has_more,
            ranked_candidates=ranked,
            unranked_candidates=unranked,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Batch ranking failure for batch '%s'", active_batch_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch ranking failed due to an unexpected server error.",
        )


# ==============================================================================
# POST /ranking/rank-batch-async
# ==============================================================================


@router.post(
    "/rank-batch-async",
    response_model=RankingJobStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue asynchronous batch ranking job for all eligible resumes",
    response_description="Returns HTTP 202 Accepted with job_id and initial tracking state immediately",
)
async def rank_batch_async(
    request: RankBatchRequest = RankBatchRequest(),
) -> RankingJobStatusResponse:
    """
    Queue an asynchronous ranking job across eligible completed resumes from the active batch.

    Returns HTTP 202 Accepted promptly with a unique job_id and tracking metadata.
    Does not block waiting for long-running LLM evaluation.
    Poll GET /ranking/jobs/{job_id} for progress and final results.
    """
    try:
        job_doc = await ranking_engine.create_and_start_ranking_job(
            upload_id=request.upload_id,
            jd_id=request.jd_id,
            limit=request.limit,
            skip=request.skip,
            use_evidence_based_experience=request.use_evidence_based_experience,
        )
        return RankingJobStatusResponse.model_validate(job_doc)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Failed to schedule asynchronous ranking job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule asynchronous ranking job due to an unexpected server error.",
        )


# ==============================================================================
# GET /ranking/jobs/{job_id}
# ==============================================================================


@router.get(
    "/jobs/{job_id}",
    response_model=RankingJobStatusResponse,
    summary="Get status, progress, and results of an asynchronous ranking job",
    response_description="Current execution status, candidate progress, and final rankings on completion",
)
async def get_ranking_job(
    job_id: str,
) -> RankingJobStatusResponse:
    """
    Poll the execution status and progress of an asynchronous ranking job.

    Returns:
    - Status: queued, processing, completed, failed, or interrupted.
    - Progress: completed_count, failed_count, total_eligible, and progress_percentage.
    - Result: Full BatchRankingResponse when status is 'completed'.
    - Error: Sanitized error description if failed or interrupted.
    """
    job_doc = await ranking_job_repository.get_job(job_id)
    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ranking job '{job_id}' not found.",
        )
    if "_id" in job_doc:
        job_doc = dict(job_doc)
        job_doc.pop("_id", None)
    return RankingJobStatusResponse.model_validate(job_doc)

