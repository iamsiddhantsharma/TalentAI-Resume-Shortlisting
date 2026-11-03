from fastapi import (
    APIRouter,
    HTTPException,
)

from app.database.mongodb import mongodb
from app.services.result_store import (
    result_store,
)


router = APIRouter(
    prefix="/results",
    tags=["Processing Results"],
)


# ============================================================
# RESUME RESULTS - IN MEMORY
# ============================================================


@router.get("/")
async def get_all_results():
    """
    Return all processed resume results
    from the in-memory ResultStore.
    """

    results = result_store.get_all()

    return {
        "total_results": len(results),
        "results": [
            result.model_dump()
            for result in results
        ],
    }


@router.get("/count")
async def get_result_count():
    """
    Return the number of stored resume results
    in the in-memory ResultStore.
    """

    return {
        "result_count": result_store.count(),
    }


# ============================================================
# JOB DESCRIPTION RESULTS - IN MEMORY
# ============================================================


@router.get("/job-descriptions")
async def get_all_job_descriptions():
    """
    Return all stored Job Description results
    from the in-memory ResultStore.
    """

    job_descriptions = (
        result_store
        .get_all_job_descriptions()
    )

    return {
        "total_job_descriptions": (
            len(job_descriptions)
        ),
        "job_descriptions": [
            jd.model_dump()
            for jd in job_descriptions
        ],
    }


@router.get("/job-descriptions/count")
async def get_job_description_count():
    """
    Return number of stored Job Descriptions
    in the in-memory ResultStore.
    """

    return {
        "job_description_count": (
            result_store
            .count_job_descriptions()
        ),
    }


@router.get("/job-descriptions/{jd_id}")
async def get_job_description(
    jd_id: str,
):
    """
    Return one stored Job Description
    using its jd_id.
    """

    result = (
        result_store
        .get_job_description(
            jd_id
        )
    )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No Job Description found "
                f"for jd_id: {jd_id}"
            ),
        )

    return result.model_dump()


# ============================================================
# RESUME RESULT BY FILE - IN MEMORY
# ============================================================


@router.get("/{filename}")
async def get_result(
    filename: str,
):
    """
    Return processing result for one resume
    from the in-memory ResultStore.
    """

    results = result_store.get_all()

    for result in results:

        if result.filename == filename:
            return result.model_dump()

    raise HTTPException(
        status_code=404,
        detail=(
            f"No processing result found "
            f"for: {filename}"
        ),
    )


# ============================================================
# MONGODB VERIFICATION
# ============================================================


@router.get(
    "/mongodb/status",
    tags=["MongoDB Verification"],
)
async def get_mongodb_status():
    """
    Verify MongoDB connection and show the
    number of documents stored in MongoDB.

    This endpoint is mainly useful during
    Phase 6 development/testing.
    """

    try:

        database = mongodb.get_database()

        resume_count = (
            await database[
                "resumes"
            ].count_documents({})
        )

        jd_count = (
            await database[
                "job_descriptions"
            ].count_documents({})
        )

        collections = (
            await database
            .list_collection_names()
        )

        return {
            "mongodb": "connected",
            "database": database.name,
            "collections": collections,
            "resume_documents": resume_count,
            "job_description_documents": jd_count,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"MongoDB verification failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# MONGODB RESUMES
# ============================================================


@router.get(
    "/mongodb/resumes",
    tags=["MongoDB Verification"],
)
async def get_mongodb_resumes():
    """
    Return resume documents directly from MongoDB.

    This verifies that processed resume data
    is actually persisted in MongoDB.
    """

    try:

        database = mongodb.get_database()

        cursor = database[
            "resumes"
        ].find({})

        documents = await cursor.to_list(
            length=None
        )

        return {
            "total_resumes": len(
                documents
            ),
            "resumes": documents,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to read resumes "
                f"from MongoDB: {str(exc)}"
            ),
        )


# ============================================================
# MONGODB JOB DESCRIPTIONS
# ============================================================


@router.get(
    "/mongodb/job-descriptions",
    tags=["MongoDB Verification"],
)
async def get_mongodb_job_descriptions():
    """
    Return Job Description documents directly
    from MongoDB.

    This verifies that processed JD data is
    actually persisted in MongoDB.
    """

    try:

        database = mongodb.get_database()

        cursor = database[
            "job_descriptions"
        ].find({})

        documents = await cursor.to_list(
            length=None
        )

        return {
            "total_job_descriptions": len(
                documents
            ),
            "job_descriptions": documents,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to read Job Descriptions "
                f"from MongoDB: {str(exc)}"
            ),
        )


# ============================================================
# CLEAR RESULTS
# ============================================================


@router.delete("/")
async def clear_results():
    """
    Clear all resume and Job Description
    results from the in-memory ResultStore.

    NOTE:
    This does NOT delete MongoDB documents.
    """

    result_store.clear()

    return {
        "status": "cleared",
        "result_count": 0,
        "job_description_count": 0,
        "mongodb": (
            "MongoDB documents were NOT deleted"
        ),
    }
