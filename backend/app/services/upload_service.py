import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status, UploadFile

from app.config.settings import settings
from app.database.batch_repository import batch_repository
from app.schemas.batch import Batch
from app.schemas.storage import StoredFile
from app.schemas.upload_response import UploadResponse
from app.services.discovery_service import discovery_service
from app.services.file_validation_service import validation_service
from app.services.ingestion_service import ingestion_service
from app.services.storage_service import storage_service, UploadSizeLimitExceeded
from app.services.zip_service import zip_service, ZipExtractionError
from app.utils.file_utils import safe_rmtree

logger = logging.getLogger(__name__)


class UploadService:
    """
    Handles the upload stage of the TalentAI pipeline.
    """

    async def create_upload_job(
        self,
        files: list[UploadFile],
        auto_activate: bool = False,
    ) -> UploadResponse:
        """
        Validate, store, extract, discover and ingest files with strict security limits:
        - Rejects uploads exceeding MAX_FILES_PER_REQUEST.
        - Streams and enforces MAX_UPLOAD_SIZE_MB per file.
        - Tracks cumulative size against MAX_REQUEST_BODY_SIZE_MB.
        - Enforces MAX_RESUMES_PER_BATCH.
        - Cleans up partial files safely on any rejection or failure.
        """

        # 1. Enforce MAX_FILES_PER_REQUEST upfront before disk I/O
        if len(files) > settings.MAX_FILES_PER_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Upload rejected: {len(files)} files received, exceeding the maximum allowed limit "
                    f"of {settings.MAX_FILES_PER_REQUEST} files per request."
                ),
            )

        upload_id = str(uuid4())
        batch_name = files[0].filename if files and files[0].filename else "Resume Upload Batch"
        now = datetime.now(timezone.utc)
        retention_delta = timedelta(hours=settings.BATCH_RETENTION_HOURS)
        draft_expiry = now + retention_delta

        # Initialize isolated recruitment batch
        # Stamped with draft expiry so abandoned drafts cannot accumulate indefinitely
        batch = Batch(
            batch_id=upload_id,
            batch_name=batch_name,
            status="draft",
            is_active=False,
            auto_activate=auto_activate,
            total_files=0,
            processed_count=0,
            completed_count=0,
            failed_count=0,
            created_at=now,
            updated_at=now,
            last_activity_at=now,
            expires_at=draft_expiry,
        )
        await batch_repository.save(batch)

        supported_files = 0
        ignored_files = 0
        failed_files = 0
        enqueued_jobs = 0

        stored_files: list[StoredFile] = []
        seen_hashes: set[str] = set()

        cumulative_bytes = 0
        max_request_bytes = settings.MAX_REQUEST_BODY_SIZE_MB * 1024 * 1024

        async def _cleanup_and_delete_batch():
            storage_service.delete_upload(upload_id)
            extracted_dir = Path(settings.EXTRACTED_DIR) / upload_id
            safe_rmtree(extracted_dir)
            await batch_repository.delete(upload_id)

        try:
            for file in files:

                if not file.filename:
                    ignored_files += 1
                    continue

                if not validation_service.is_supported(
                    file.filename
                ):
                    ignored_files += 1
                    continue

                try:
                    stored_file = await storage_service.save_file(
                        file=file,
                        upload_id=upload_id,
                    )
                except UploadSizeLimitExceeded as e:
                    logger.warning("Upload size exceeded for %s: %s", file.filename, e)
                    await _cleanup_and_delete_batch()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=str(e),
                    )

                # Check cumulative payload size limit
                cumulative_bytes += stored_file.file_size
                if cumulative_bytes > max_request_bytes:
                    logger.warning(
                        "Cumulative upload size (%d bytes) exceeded body limit of %d bytes for upload %s",
                        cumulative_bytes,
                        max_request_bytes,
                        upload_id,
                    )
                    await _cleanup_and_delete_batch()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"Total upload payload exceeds the maximum allowed request limit "
                            f"of {settings.MAX_REQUEST_BODY_SIZE_MB}MB."
                        ),
                    )

                # ----------------------------------------------
                # Exact duplicate detection
                # ----------------------------------------------

                if stored_file.sha256 in seen_hashes:

                    ignored_files += 1

                    Path(
                        stored_file.file_path
                    ).unlink(
                        missing_ok=True
                    )

                    continue

                seen_hashes.add(
                    stored_file.sha256
                )

                # ----------------------------------------------
                # ZIP
                # ----------------------------------------------

                if stored_file.file_extension == ".zip":

                    try:
                        extraction_directory = (
                            await zip_service.extract_zip(
                                zip_path=stored_file.file_path,
                                upload_id=upload_id,
                            )
                        )
                    except ZipExtractionError as exc:
                        logger.warning("ZIP extraction rejected for upload %s: %s", upload_id, exc)
                        await _cleanup_and_delete_batch()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Archive validation failed: {str(exc)}",
                        )

                    discovered_files = (
                        discovery_service.discover_files(
                            extraction_directory
                        )
                    )

                    # Check max resumes per batch limit
                    if enqueued_jobs + len(discovered_files) > settings.MAX_RESUMES_PER_BATCH:
                        logger.warning(
                            "Batch resume limit exceeded (%d + %d > %d) for upload %s",
                            enqueued_jobs,
                            len(discovered_files),
                            settings.MAX_RESUMES_PER_BATCH,
                            upload_id,
                        )
                        await _cleanup_and_delete_batch()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Batch candidate limit exceeded: batch would contain "
                                f"{enqueued_jobs + len(discovered_files)} resumes, exceeding maximum limit "
                                f"of {settings.MAX_RESUMES_PER_BATCH} resumes per batch."
                            ),
                        )

                    for discovered_file in discovered_files:

                        await (
                            ingestion_service
                            .ingest_discovered_file(
                                upload_id=upload_id,
                                discovered_file=discovered_file,
                            )
                        )
                        enqueued_jobs += 1

                # ----------------------------------------------
                # Direct PDF / DOCX / TXT
                # ----------------------------------------------

                else:

                    if enqueued_jobs + 1 > settings.MAX_RESUMES_PER_BATCH:
                        await _cleanup_and_delete_batch()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                f"Batch candidate limit exceeded: maximum allowed is "
                                f"{settings.MAX_RESUMES_PER_BATCH} candidate resumes per batch."
                            ),
                        )

                    await (
                        ingestion_service
                        .ingest_direct_file(
                            upload_id=upload_id,
                            file_path=stored_file.file_path,
                            filename=stored_file.original_filename,
                        )
                    )
                    enqueued_jobs += 1

                stored_files.append(
                    stored_file
                )

                supported_files += 1

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error processing upload %s: %s", upload_id, e)
            await _cleanup_and_delete_batch()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred during file upload processing.",
            )

        # ----------------------------------------------
        # Update Batch State
        # ----------------------------------------------

        if enqueued_jobs > 0:
            batch_status = "processing"
            await batch_repository.update_status(
                batch_id=upload_id,
                status="processing",
                total_files=enqueued_jobs,
                clear_expires_at=True,
            )
        else:
            batch_status = "failed"
            now = datetime.now(timezone.utc)
            retention_delta = timedelta(hours=settings.BATCH_RETENTION_HOURS)
            expires_at = (now + retention_delta).isoformat()

            failure_reasons = []
            if not files:
                failure_reasons.append("No files provided in upload request.")
            elif ignored_files == len(files):
                failure_reasons.append("All files were unsupported or duplicate.")
            elif failed_files > 0:
                failure_reasons.append(f"{failed_files} file(s) failed during extraction or validation.")
            else:
                failure_reasons.append("Zero candidate resumes discovered.")

            await batch_repository.update_status(
                batch_id=upload_id,
                status="failed",
                total_files=0,
                expires_at=expires_at,
                metadata={
                    "error_reason": "; ".join(failure_reasons),
                    "failed_files": failed_files,
                    "ignored_files": ignored_files,
                    "total_files_received": len(files),
                },
            )

        # ----------------------------------------------
        # Response message
        # ----------------------------------------------

        if failed_files > 0 and supported_files > 0:
            message = "Files accepted with some failures."
        elif failed_files > 0:
            message = "File processing failed for one or more files."
        elif ignored_files > 0:
            message = "Files accepted with some ignored files."
        else:
            message = "Files accepted and queued for processing."

        if supported_files > 0:
            if auto_activate:
                message += f" Batch '{upload_id}' will automatically activate for matching upon completion."
            else:
                message += (
                    f" Batch '{upload_id}' will enter 'ready' status once processing completes. "
                    f"Activate it via POST /batches/{upload_id}/activate before matching, "
                    "or upload with auto_activate=true."
                )

        return UploadResponse(
            status="accepted" if supported_files > 0 else "failed",
            upload_id=upload_id,
            batch_id=upload_id,
            batch_status=batch_status,
            total_files_received=len(files),
            supported_files=supported_files,
            ignored_files=ignored_files,
            failed_files=failed_files,
            stored_files=stored_files,
            message=message,
        )

    def _move_to_failed_directory(
        self,
        file_path: str,
        upload_id: str,
    ) -> None:
        """
        Move a failed file into the failed directory.
        """

        source = Path(file_path)

        if not source.exists():
            return

        failed_directory = (
            Path(settings.FAILED_DIR)
            / upload_id
        )

        failed_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            failed_directory
            / source.name
        )

        source.replace(
            destination
        )


upload_service = UploadService()
