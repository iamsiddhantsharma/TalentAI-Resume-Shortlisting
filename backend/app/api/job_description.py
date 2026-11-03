from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import (
    APIRouter,
    Body,
    File,
    HTTPException,
    UploadFile,
)

from pydantic import BaseModel, Field

from app.database.jd_repository import (
    jd_repository,
)

from app.services.job_description_service import (
    job_description_service,
)

from app.services.jd_embedding_generation_service import (
    job_description_embedding_generation_service,
)

from app.services.result_store import (
    result_store,
)


router = APIRouter(
    prefix="/job-description",
    tags=["Job Description"],
)


# ============================================================
# JSON REQUEST MODEL
# ============================================================


class JobDescriptionTextRequest(BaseModel):
    """
    Request body for JSON Job Description input.

    Example:

    {
        "text": "We are looking for a Python developer..."
    }
    """

    text: str = Field(
        min_length=1,
        description="Job Description text.",
    )


# ============================================================
# FILE ENDPOINT
# ============================================================


@router.post("/file")
async def upload_job_description(
    file: UploadFile = File(
        ...,
        description=(
            "Job Description file. "
            "Supported formats: PDF, DOCX, TXT."
        ),
    ),
):
    """
    Upload and process a Job Description file.

    Supported:
        PDF
        DOCX
        TXT

    The processed Job Description is stored in:

        1. In-memory ResultStore
        2. MongoDB
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    extension = (
        Path(file.filename)
        .suffix
        .lower()
    )

    if extension not in {
        ".pdf",
        ".docx",
        ".txt",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported Job Description file type. "
                "Only PDF, DOCX and TXT are supported."
            ),
        )

    temporary_path = None

    try:

        # ----------------------------------------------------
        # Read uploaded file
        # ----------------------------------------------------

        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Uploaded Job Description "
                    "file is empty."
                ),
            )

        # ----------------------------------------------------
        # Create temporary file
        # ----------------------------------------------------

        with NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temporary_file:

            temporary_file.write(
                file_content
            )

            temporary_path = Path(
                temporary_file.name
            )

        # ----------------------------------------------------
        # Process JD
        # ----------------------------------------------------

        result = (
            await job_description_service
            .process_file(
                file_path=str(
                    temporary_path
                ),
                filename=file.filename,
            )
        )

        # ----------------------------------------------------
        # STORE JD RESULT
        # ----------------------------------------------------

        # Existing in-memory storage
        result_store.save_job_description(
            result
        )

        # MongoDB persistent storage
        await jd_repository.save(
            result
        )

        # Generate and store active JD embeddings
        await job_description_embedding_generation_service.generate_for_jd(
            result.jd_id
        )

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        print()
        print("========================================")
        print("JOB DESCRIPTION STORED")
        print("========================================")

        print(
            "JD ID:",
            result.jd_id,
        )

        print(
            "Input type:",
            result.input_type,
        )

        print(
            "Filename:",
            result.filename,
        )

        print(
            "In-memory JD count:",
            result_store.count_job_descriptions(),
        )

        print(
            "MongoDB JD stored: YES"
        )

        print("========================================")

        return result

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    finally:

        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


# ============================================================
# JSON TEXT ENDPOINT
# ============================================================


@router.post("/text")
async def process_job_description_text(
    request: JobDescriptionTextRequest,
):
    """
    Process a Job Description supplied as JSON.

    Content-Type:

        application/json

    Example:

    {
        "text": "We are looking for a Python developer..."
    }

    The processed Job Description is stored in:

        1. In-memory ResultStore
        2. MongoDB
    """

    try:

        # ----------------------------------------------------
        # Validate text
        # ----------------------------------------------------

        if not request.text.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Job Description text "
                    "cannot be empty."
                ),
            )

        # ----------------------------------------------------
        # Process JD
        # ----------------------------------------------------

        result = (
            await job_description_service
            .process_text(
                request.text
            )
        )

        # ----------------------------------------------------
        # STORE JD RESULT
        # ----------------------------------------------------

        # Existing in-memory storage
        result_store.save_job_description(
            result
        )

        # MongoDB persistent storage
        await jd_repository.save(
            result
        )

        # Generate and store active JD embeddings
        await job_description_embedding_generation_service.generate_for_jd(
            result.jd_id
        )

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        print()
        print("========================================")
        print("JSON JD STORED")
        print("========================================")

        print(
            "JD ID:",
            result.jd_id,
        )

        print(
            "In-memory JD count:",
            result_store.count_job_descriptions(),
        )

        print(
            "MongoDB JD stored: YES"
        )

        print("========================================")

        return result

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )


# ============================================================
# RAW TEXT ENDPOINT
# ============================================================


@router.post("/raw")
async def process_job_description_raw(
    text: str = Body(
        ...,
        media_type="text/plain",
        description=(
            "Raw pasted Job Description text."
        ),
    ),
):
    """
    Process a Job Description supplied as
    raw plain text.

    Content-Type:

        text/plain

    Example body:

        We are looking for a Python Developer.
        2-5 years of experience required.
        Strong Python and FastAPI skills required.

    The processed Job Description is stored in:

        1. In-memory ResultStore
        2. MongoDB
    """

    print()
    print("========================================")
    print("RAW JD ENDPOINT CALLED")
    print("========================================")

    print(
        "Text type:",
        type(text),
    )

    print(
        "Text length:",
        len(text),
    )

    print(
        "First 300 characters:"
    )

    print(
        text[:300]
    )

    print(
        "========================================"
    )

    try:

        # ----------------------------------------------------
        # Validate raw text
        # ----------------------------------------------------

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Job Description text "
                    "cannot be empty."
                ),
            )

        print()
        print(
            "Sending JD to "
            "JobDescriptionService..."
        )

        # ----------------------------------------------------
        # Process JD
        # ----------------------------------------------------

        result = (
            await job_description_service
            .process_text(
                text
            )
        )

        # ----------------------------------------------------
        # STORE JD RESULT
        # ----------------------------------------------------

        # Existing in-memory storage
        result_store.save_job_description(
            result
        )

        # MongoDB persistent storage
        await jd_repository.save(
            result
        )

        # Generate and store active JD embeddings
        await job_description_embedding_generation_service.generate_for_jd(
            result.jd_id
        )

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        print()
        print("========================================")
        print("RAW JD PROCESSING SUCCESSFUL")
        print("========================================")

        print(
            "JD ID:",
            result.jd_id,
        )

        print(
            "In-memory JD count:",
            result_store.count_job_descriptions(),
        )

        print(
            "MongoDB JD stored: YES"
        )

        print(
            "========================================"
        )

        return result

    except HTTPException:
        raise

    except Exception as exc:

        print()
        print("========================================")
        print("RAW JD PROCESSING FAILED")
        print("========================================")

        print(
            "Exception type:",
            type(exc).__name__,
        )

        print(
            "Exception:",
            repr(exc),
        )

        print(
            "Exception message:",
            str(exc),
        )

        print(
            "========================================"
        )

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
