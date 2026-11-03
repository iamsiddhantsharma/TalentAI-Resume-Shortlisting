import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.auth import (
    router as auth_router,
)
from app.auth.auth_dependencies import (
    get_current_hr_user,
)
from app.auth.auth_service import (
    auth_service,
)
from app.api.batches import (
    router as batches_router,
)
from app.api.job_description import (
    router as job_description_router,
)
from app.api.matching import (
    router as matching_router,
)
from app.api.ranking import (
    router as ranking_router,
)
from app.api.demo import router as demo_router
from app.api.queue import router as queue_router
from app.api.results import router as results_router
from app.api.status import router as status_router
from app.api.upload import router as upload_router
from app.config.settings import settings
from app.core.logger import logger
from app.database.batch_repository import (
    batch_repository,
)
from app.database.jd_repository import (
    jd_repository,
)
from app.database.mongodb import mongodb
from app.database.ranking_job_repository import (
    ranking_job_repository,
)
from app.database.resume_repository import (
    resume_repository,
)
from app.ranking.ranking_service import (
    ranking_engine,
)

from app.queue.worker import (
    start_worker,
    stop_worker,
)
from app.services.retention_service import (
    start_retention_task,
    stop_retention_task,
)
from app.services.ai_lifecycle_manager import (
    ai_lifecycle_manager,
)
from app.services.result_store import (
    result_store,
)
from app.utils.file_utils import (
    create_upload_directories,
)


# ============================================================
# PRIVACY CLEANUP
# ============================================================


async def cleanup_session_data() -> None:
    """
    Remove all temporary TalentAI data.

    Cleanup is performed in three places:

        1. MongoDB
        2. In-memory ResultStore
        3. Local uploaded files

    This function is intended to run when the
    FastAPI application shuts down.
    """

    logger.info(
        "Starting TalentAI privacy cleanup..."
    )

    # --------------------------------------------------------
    # 1. Delete resumes from MongoDB
    # --------------------------------------------------------

    try:

        await resume_repository.delete_all()

        logger.info(
            "All resume data deleted from MongoDB."
        )

    except Exception:

        logger.exception(
            "Failed to delete resume data from MongoDB."
        )

    # --------------------------------------------------------
    # 2. Delete Job Descriptions from MongoDB
    # --------------------------------------------------------

    try:

        await jd_repository.delete_all()

        logger.info(
            "All Job Description data deleted from MongoDB."
        )

    except Exception:

        logger.exception(
            "Failed to delete Job Description data from MongoDB."
        )

    # --------------------------------------------------------
    # 3. Clear in-memory ResultStore
    # --------------------------------------------------------

    try:

        result_store.clear()

        logger.info(
            "In-memory ResultStore cleared."
        )

    except Exception:

        logger.exception(
            "Failed to clear in-memory ResultStore."
        )

    # --------------------------------------------------------
    # 4. Delete local uploaded files
    # --------------------------------------------------------

    try:

        upload_directory = Path(
            settings.UPLOAD_DIR
        )

        if upload_directory.exists():

            for item in upload_directory.iterdir():

                try:

                    if item.is_dir():

                        shutil.rmtree(
                            item
                        )

                    elif item.is_file():

                        item.unlink()

                except Exception:

                    logger.exception(
                        "Failed to delete local upload item: %s",
                        item,
                    )

            logger.info(
                "Local uploaded files deleted."
            )

        else:

            logger.info(
                "Upload directory does not exist. "
                "Nothing to delete."
            )

    except Exception:

        logger.exception(
            "Failed to clean local uploaded files."
        )

    logger.info(
        "TalentAI privacy cleanup completed."
    )


# ============================================================
# APPLICATION LIFESPAN
# ============================================================


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Manage application startup and shutdown.

    Startup:
        1. Connect MongoDB
        2. Initialize MongoDB indexes and legacy batch consistency
        3. Start resume worker
        4. Start retention maintenance task

    Shutdown:
        1. Stop retention maintenance task
        2. Stop resume worker
        3. Disconnect MongoDB (preserves all persistent recruitment data)
    """

    # ========================================================
    # STARTUP
    # ========================================================

    logger.info(
        "Starting TalentAI application..."
    )

    # --------------------------------------------------------
    # 1. Connect MongoDB
    # --------------------------------------------------------

    await mongodb.connect()

    logger.info(
        "MongoDB connected successfully."
    )

    # --------------------------------------------------------
    # 2. Initialize Indexes and Legacy Batch Consistency
    # --------------------------------------------------------

    await batch_repository.create_indexes()
    await batch_repository.ensure_legacy_batch_consistency()
    await ranking_job_repository.create_indexes()
    await ranking_job_repository.reconcile_stale_jobs()
    await auth_service.create_indexes()
    await auth_service.ensure_initial_hr_user()

    # --------------------------------------------------------
    # 3. Start resume worker
    # --------------------------------------------------------

    await start_worker()

    logger.info(
        "Resume worker started successfully."
    )

    # --------------------------------------------------------
    # 4. Start retention maintenance task
    # --------------------------------------------------------

    await start_retention_task()

    logger.info(
        "Retention maintenance task started."
    )

    try:

        yield

    finally:

        # ====================================================
        # SHUTDOWN
        # ====================================================

        logger.info(
            "Stopping TalentAI application..."
        )

        # ----------------------------------------------------
        # 1. Cancel in-flight background ranking jobs
        # ----------------------------------------------------

        await ranking_engine.cancel_all_jobs()

        # ----------------------------------------------------
        # 2. Stop retention maintenance task
        # ----------------------------------------------------

        await stop_retention_task()

        # ----------------------------------------------------
        # 3. Stop resume worker
        # ----------------------------------------------------

        await stop_worker()

        logger.info(
            "Resume worker stopped."
        )

        # ----------------------------------------------------
        # 4. Stop Ollama process if managed by AI lifecycle
        # ----------------------------------------------------

        await ai_lifecycle_manager.stop_ollama(force=True)

        # ----------------------------------------------------
        # 5. Disconnect MongoDB (PRESERVES ALL PERSISTENT DATA)
        # ----------------------------------------------------

        await mongodb.disconnect()

        logger.info(
            "MongoDB disconnected successfully."
        )

        logger.info(
            "TalentAI application stopped safely (persistent records preserved)."
        )


# ============================================================
# FASTAPI APPLICATION
# ============================================================


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ------------------------------------------------------------
# 1. CORRELATION / REQUEST ID MIDDLEWARE
# ------------------------------------------------------------

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Ensure every HTTP request has a unique correlation ID.
    Attaches to request.state, logs unhandled errors with request_id,
    and guarantees sanitized 500 responses without traceback leakage.
    """
    request_id = request.headers.get("X-Request-ID")
    if not request_id or not request_id.strip():
        request_id = str(uuid4())
    else:
        request_id = request_id.strip()

    request.state.request_id = request_id

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "Unhandled internal server error [request_id=%s] on %s %s: %s",
            request_id,
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. Please contact system support with the request ID.",
                "request_id": request_id,
            },
        )

    response.headers["X-Request-ID"] = request_id
    return response


# ------------------------------------------------------------
# 2. CORS SECURITY TIGHTENING
# ------------------------------------------------------------

cors_origins = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

# Security requirement: Never allow wildcard '*' when credentials are permitted
if "*" in cors_origins:
    logger.warning("Wildcard CORS origin '*' with credentials enabled is disallowed. Removing wildcard.")
    cors_origins = [o for o in cors_origins if o != "*"]

if not cors_origins:
    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "Accept"],
    expose_headers=["X-Request-ID"],
)


# ------------------------------------------------------------
# 3. GLOBAL SANITIZED EXCEPTION HANDLERS
# ------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Sanitized HTTP exception response with correlation ID."""
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    headers = dict(exc.headers or {})
    headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
        },
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global 500 handler: logs full stack trace internally with request_id,
    and returns a clean, sanitized error response with zero leakage of
    file paths, tracebacks, database details, or secrets.
    """
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    logger.error(
        "Unhandled internal server error [request_id=%s] on %s %s: %s",
        request_id,
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please contact system support with the request ID.",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


# ============================================================
# CREATE UPLOAD DIRECTORIES
# ============================================================


create_upload_directories()

logger.info(
    "TalentAI started successfully."
)


# ============================================================
# API ROUTES
# ============================================================


# 1. Public Authentication Router
app.include_router(
    auth_router
)

# 2. Protected Application Routers (HR Team Only)
app.include_router(
    upload_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    batches_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    status_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    queue_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    results_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    job_description_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    matching_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    ranking_router,
    dependencies=[Depends(get_current_hr_user)],
)

app.include_router(
    demo_router,
    dependencies=[Depends(get_current_hr_user)],
)


# ============================================================
# CUSTOM OPENAPI
# ============================================================


def custom_openapi():
    """
    Patch FastAPI OpenAPI so Swagger UI correctly
    renders UploadFile fields.
    """

    if app.openapi_schema:

        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    for component in (
        schema
        .get("components", {})
        .get("schemas", {})
        .values()
    ):

        for prop in component.get(
            "properties",
            {},
        ).values():

            if (
                prop.get("contentMediaType")
                == "application/octet-stream"
            ):

                del prop[
                    "contentMediaType"
                ]

                prop["format"] = "binary"

            items = prop.get(
                "items",
                {},
            )

            if (
                items.get("contentMediaType")
                == "application/octet-stream"
            ):

                del items[
                    "contentMediaType"
                ]

                items["format"] = "binary"

    app.openapi_schema = schema

    return schema


app.openapi = custom_openapi


# ============================================================
# ROOT ENDPOINT
# ============================================================


@app.get("/")
def home():

    return {
        "message": (
            "TalentAI Resume Intelligence System"
        )
    }


@app.get("/health", tags=["Health"])
def health_check():
    """
    Public lightweight liveness check for reverse proxy / container health.
    Does not expose sensitive candidate data or database internals.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
