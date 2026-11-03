import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path

from app.config.settings import settings
from app.database.batch_repository import batch_repository
from app.database.resume_embedding_repository import resume_embedding_repository
from app.database.resume_repository import resume_repository
from app.services.storage_service import storage_service
from app.utils.file_utils import safe_rmtree

logger = logging.getLogger(__name__)

# Mandatory protected batch ID (145-resume processing batch)
PROTECTED_BATCH_ID = "93cce6d0-3f25-4bdb-b11a-c423caf5f6b0"


class RetentionService:
    """
    Manages controlled lifecycle retention and cleanup for recruitment batches.

    Guarantees:
    - Currently active batch is NEVER expired or cleaned up.
    - Active Job Description and JD embeddings are NEVER touched.
    - Protected batch 93cce6d0-3f25-4bdb-b11a-c423caf5f6b0 is completely preserved.
    - Filesystem paths are deleted first using safe_rmtree.
    - On filesystem deletion failure, batch document is retained with failure metadata for later retry.
    - Only records and files explicitly belonging to expired/discarded batches are deleted.
    - Application shutdown does not trigger global cleanup.
    - Interrupted cleanup is idempotent and safe to resume.
    """

    def __init__(self):
        self._lock = asyncio.Lock()

    def _delete_batch_files(self, batch_id: str) -> tuple[bool, str | None]:
        """
        Delete all filesystem paths associated with batch_id:
        - Incoming upload directory (via storage_service.delete_upload)
        - Extracted directory
        - Failed directory

        Uses safe_rmtree to handle Windows read-only attributes, symlink protection,
        and bounded retries for transient locks.

        Returns:
            (success: bool, error_message: str | None)
        """
        # 1. Incoming upload folder
        try:
            storage_service.delete_upload(batch_id)
        except Exception as exc:
            err = f"Failed to delete upload directory for batch '{batch_id}': {type(exc).__name__}: {exc}"
            logger.warning(err)
            return False, err

        # 2. Extracted files folder
        try:
            base_extracted = Path(settings.EXTRACTED_DIR).resolve()
            extracted_batch_dir = (base_extracted / batch_id).resolve()
            try:
                extracted_batch_dir.relative_to(base_extracted)
            except ValueError:
                err = f"Path traversal detected in extracted dir for batch '{batch_id}'"
                logger.warning(err)
                return False, err

            if extracted_batch_dir.exists():
                safe_rmtree(extracted_batch_dir, ignore_errors=False)
        except Exception as exc:
            err = f"Failed to delete extracted directory for batch '{batch_id}': {type(exc).__name__}: {exc}"
            logger.warning(err)
            return False, err

        # 3. Failed files folder
        try:
            base_failed = Path(settings.FAILED_DIR).resolve()
            failed_batch_dir = (base_failed / batch_id).resolve()
            try:
                failed_batch_dir.relative_to(base_failed)
            except ValueError:
                err = f"Path traversal detected in failed dir for batch '{batch_id}'"
                logger.warning(err)
                return False, err

            if failed_batch_dir.exists():
                safe_rmtree(failed_batch_dir, ignore_errors=False)
        except Exception as exc:
            err = f"Failed to delete failed directory for batch '{batch_id}': {type(exc).__name__}: {exc}"
            logger.warning(err)
            return False, err

        return True, None

    async def _delete_batch_records(self, batch_id: str) -> tuple[int, int]:
        """
        Delete resumes and embeddings from MongoDB for one batch.
        Returns (resumes_count, embeddings_count).
        """
        try:
            col_res = resume_repository._collection()
            resumes_count = await col_res.count_documents({"upload_id": batch_id}) if col_res is not None else 0
        except Exception:
            resumes_count = 0

        try:
            col_emb = resume_embedding_repository._collection()
            embeddings_count = await col_emb.count_documents({"upload_id": batch_id}) if col_emb is not None else 0
        except Exception:
            embeddings_count = 0

        await resume_repository.delete_by_upload(batch_id)
        await resume_embedding_repository.delete_by_upload(batch_id)
        return resumes_count, embeddings_count

    async def _delete_batch_records_and_files(self, batch_id: str) -> tuple[int, int]:
        """
        Delete filesystem files first, then database records.
        Preserves backwards-compatibility with existing callers and tests.
        """
        files_deleted, fs_error = self._delete_batch_files(batch_id)
        if not files_deleted:
            raise OSError(f"Filesystem deletion failed: {fs_error}")

        return await self._delete_batch_records(batch_id)

    async def cleanup_expired_batches(self) -> int:
        """
        Scan and remove expired inactive batches.
        Thread/task safe and idempotent.

        Guarantees:
        - Confirms each batch is expired and inactive before proceeding.
        - Preserves protected batch 93cce6d0-3f25-4bdb-b11a-c423caf5f6b0 completely.
        - Deletes filesystem paths before finalizing MongoDB deletion.
        - On filesystem deletion failure, retains metadata on the batch for later retry
          and does NOT delete the batch document.
        - Continues processing subsequent batches if one batch encounters an error.

        Returns the number of batches cleaned up.
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_batches = await batch_repository.get_expired_batches(now)

            if not expired_batches:
                logger.debug("No expired recruitment batches found for cleanup.")
                return 0

        logger.info(
            "Found %d expired recruitment batches to clean up.",
            len(expired_batches),
        )

        cleaned_count = 0
        for batch in expired_batches:
            batch_id = batch.get("batch_id") or batch.get("_id")
            if not batch_id:
                continue

            # CRITICAL SAFETY CHECK: Never delete protected 145-resume batch
            if batch_id == PROTECTED_BATCH_ID:
                logger.warning(
                    "Safety guard: Protected batch '%s' encountered during expired cleanup. Skipping.",
                    batch_id,
                )
                continue

            # CRITICAL SAFETY CHECK: Never delete an active batch
            if batch.get("is_active", False):
                logger.warning(
                    "Safety guard: Batch '%s' is marked active. Skipping retention cleanup.",
                    batch_id,
                )
                continue

            # Verify batch has an expiration timestamp
            if not batch.get("expires_at"):
                logger.warning(
                    "Safety guard: Batch '%s' has no expiration timestamp. Skipping retention cleanup.",
                    batch_id,
                )
                continue

            try:
                # Step 1: Delete filesystem paths first using safe_rmtree
                files_deleted, fs_error = self._delete_batch_files(batch_id)
                if not files_deleted:
                    logger.warning(
                        "Filesystem cleanup failed for expired batch '%s': %s. Retaining metadata for later retry.",
                        batch_id,
                        fs_error,
                    )
                    await batch_repository.record_cleanup_failure(
                        batch_id,
                        fs_error or "Filesystem deletion failed",
                    )
                    # Skip MongoDB deletion so batch is retained for later retry
                    continue

                # Step 2: Only finalize MongoDB deletion when filesystem cleanup succeeded
                await self._delete_batch_records(batch_id)
                await batch_repository.delete(batch_id)
                cleaned_count += 1
                logger.info("Successfully cleaned up expired batch: %s", batch_id)

            except Exception as exc:
                logger.exception(
                    "Failed to clean up expired batch: %s",
                    batch_id,
                )
                try:
                    await batch_repository.record_cleanup_failure(
                        batch_id,
                        f"{type(exc).__name__}: {exc}",
                    )
                except Exception:
                    pass
                # Continue loop to process remaining batches

        return cleaned_count

    async def discard_batch(
        self,
        batch_id: str,
        force: bool = False,
    ) -> dict:
        """
        Explicitly discard/delete a specific batch and all its associated data.

        If the batch is currently active, requires force=True to prevent accidental deletion.
        """
        if batch_id == PROTECTED_BATCH_ID:
            raise ValueError(f"Batch '{batch_id}' is protected and cannot be discarded.")

        async with self._lock:
            batch = await batch_repository.get(batch_id)
            if not batch:
                raise ValueError(f"Batch '{batch_id}' not found.")

            if batch.get("is_active", False) and not force:
                raise ValueError(
                    f"Batch '{batch_id}' is currently active. "
                    "Switch to a different active batch before discarding, or specify force=True."
                )

            # Mark batch as cancelled first so any in-flight workers immediately drop jobs
            await batch_repository.cancel_batch(batch_id)

            # Delete filesystem files first
            files_deleted, fs_error = self._delete_batch_files(batch_id)
            if not files_deleted:
                await batch_repository.record_cleanup_failure(
                    batch_id,
                    fs_error or "Filesystem cleanup failed",
                )
                raise OSError(f"Failed to delete files for batch '{batch_id}': {fs_error}")

            # Delete database records
            resumes_deleted, embeddings_deleted = await self._delete_batch_records(batch_id)

            # Delete batch document
            await batch_repository.delete(batch_id)

            logger.info("Batch '%s' successfully discarded.", batch_id)
            return {
                "batch_id": batch_id,
                "resumes_deleted": resumes_deleted,
                "embeddings_deleted": embeddings_deleted,
            }

    async def run_retention_loop(self) -> None:
        """
        Background maintenance loop for periodic cleanup of expired batches.
        """
        logger.info(
            "Retention maintenance task started (interval: %d minutes).",
            settings.BATCH_CLEANUP_INTERVAL_MINUTES,
        )

        interval_seconds = max(60, settings.BATCH_CLEANUP_INTERVAL_MINUTES * 60)

        while True:
            try:
                await self.cleanup_expired_batches()
            except Exception:
                logger.exception("Error during scheduled retention cleanup.")

            await asyncio.sleep(interval_seconds)


retention_service = RetentionService()

_retention_task: asyncio.Task | None = None


async def start_retention_task() -> None:
    """
    Start the background retention maintenance task.
    """
    global _retention_task
    if _retention_task is not None and not _retention_task.done():
        return

    _retention_task = asyncio.create_task(
        retention_service.run_retention_loop()
    )
    logger.info("Retention maintenance background task created.")


async def stop_retention_task() -> None:
    """
    Stop the background retention maintenance task cleanly.
    Normal shutdown must not delete data.
    """
    global _retention_task
    if _retention_task is None:
        return

    _retention_task.cancel()
    try:
        await _retention_task
    except asyncio.CancelledError:
        pass
    finally:
        _retention_task = None

    logger.info("Retention maintenance background task stopped.")
