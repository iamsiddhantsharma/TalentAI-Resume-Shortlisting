import asyncio
import logging

import httpx

from app.config.settings import settings
from app.database.batch_repository import (
    batch_repository,
)
from app.database.resume_embedding_repository import (
    resume_embedding_repository,
)
from app.database.resume_repository import (
    resume_repository,
)
from app.parser.parser_factory import parser_factory
from app.queue.local_queue import local_queue
from app.schemas.processing_job import ProcessingJob
from app.schemas.processing_result import ProcessingResult
from app.services.extraction_recovery import (
    extraction_recovery_service,
)
from app.services.llm_service import llm_service
from app.services.resume_embedding_generation_service import (
    resume_embedding_generation_service,
)
from app.services.result_store import result_store
from app.services.text_normalizer import text_normalizer


logger = logging.getLogger(__name__)


class ResumeWorker:
    """
    Background worker that consumes ProcessingJob objects
    from the queue and processes resumes.

    Pipeline:

        Queue
          ↓
        ParserFactory
          ↓
        Parser
          ↓
        Text Normalizer
          ↓
        LLM Extraction
          ↓
        Pydantic Validation
          ↓
        Error Recovery
          ↓
        Result Store
          ↓
        MongoDB
    """

    def __init__(
        self,
        recovery_timeout: float | None = None,
        health_check_interval: float | None = None,
    ) -> None:
        self._ollama_available: bool = True
        self.recovery_timeout = recovery_timeout
        self.health_check_interval = health_check_interval

    @property
    def effective_recovery_timeout(self) -> float:
        if self.recovery_timeout is not None:
            return self.recovery_timeout
        return getattr(settings, "OLLAMA_RECOVERY_TIMEOUT_SECONDS", 60.0)

    @property
    def effective_health_check_interval(self) -> float:
        if self.health_check_interval is not None:
            return self.health_check_interval
        return getattr(settings, "OLLAMA_HEALTH_CHECK_INTERVAL", 2.0)

    async def check_ollama_health(self) -> bool:
        """
        Perform a lightweight ping to verify Ollama availability.
        """
        return await llm_service.check_health()

    async def _wait_for_ollama_recovery(
        self,
        timeout: float | None = None,
    ) -> bool:
        """
        Polls the Ollama service health check until recovery or deadline.
        """
        effective_timeout = (
            timeout
            if timeout is not None
            else self.effective_recovery_timeout
        )
        interval = self.effective_health_check_interval
        deadline = asyncio.get_running_loop().time() + effective_timeout

        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(interval)
            if await self.check_ollama_health():
                self._ollama_available = True
                return True

        return False

    async def _pause_until_ollama_healthy(
        self,
        poll_interval: float | None = None,
    ) -> None:
        """
        Pauses queue consumption until Ollama service is healthy again.
        """
        interval = (
            poll_interval
            or self.effective_health_check_interval
        )
        while not await self.check_ollama_health():
            await asyncio.sleep(interval)
        self._ollama_available = True

    async def process_job(
        self,
        job: ProcessingJob,
    ) -> ProcessingResult:

        logger.info(
            "Processing resume: %s",
            job.filename,
        )

        logger.info(
            "Job details | filename=%s | extension=%r | path=%s",
            job.filename,
            job.file_extension,
            job.file_path,
        )

        # ------------------------------------------------------
        # Check if batch has been cancelled or expired
        # ------------------------------------------------------
        if await batch_repository.is_cancelled_or_expired(job.upload_id):
            logger.info(
                "Batch '%s' has been cancelled or expired. Skipping processing for %s.",
                job.upload_id,
                job.filename,
            )
            return ProcessingResult(
                upload_id=job.upload_id,
                filename=job.filename,
                file_path=job.file_path,
                file_extension=job.file_extension,
                relative_path=job.relative_path,
                source_folder=job.source_folder,
                folder_chain=job.folder_chain,
                folder_depth=job.folder_depth,
                is_root_level=job.is_root_level,
                status="failed",
                text=None,
                resume_data=None,
                error=f"Batch {job.upload_id} has been cancelled or expired.",
            )

        try:

            # --------------------------------------------------
            # 1. Select parser
            # --------------------------------------------------

            parser = parser_factory.get_parser(
                job.file_extension
            )

            # --------------------------------------------------
            # 2. Extract raw text
            # --------------------------------------------------

            text = parser.parse(
                job.file_path
            )

            # --------------------------------------------------
            # 3. Normalize extracted text
            # --------------------------------------------------

            normalized_text = (
                text_normalizer.normalize(
                    text
                )
            )

            # --------------------------------------------------
            # 4. LLM structured extraction
            #
            # ExtractionRecoveryService handles:
            # - Qwen
            # - JSON generation
            # - Pydantic validation
            # - correction retries
            # - maximum 3 attempts
            # --------------------------------------------------

            try:
                resume_data = (
                    await extraction_recovery_service
                    .extract_resume(
                        normalized_text
                    )
                )
            except (
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.ConnectTimeout,
            ) as exc:
                logger.warning(
                    "Ollama became unreachable during extraction of '%s' (%s). Entering recovery window...",
                    job.filename,
                    type(exc).__name__,
                )
                recovered = await self._wait_for_ollama_recovery()
                if recovered:
                    logger.info(
                        "Ollama service recovered. Retrying extraction for '%s'...",
                        job.filename,
                    )
                    resume_data = (
                        await extraction_recovery_service
                        .extract_resume(
                            normalized_text
                        )
                    )
                else:
                    self._ollama_available = False
                    logger.error(
                        "Ollama service remained unreachable after recovery window of %.1fs.",
                        self.effective_recovery_timeout,
                    )
                    try:
                        await batch_repository.update_status(
                            batch_id=job.upload_id,
                            status="processing",
                            metadata={
                                "infrastructure_alert": (
                                    f"Ollama service unreachable at {settings.OLLAMA_BASE_URL} "
                                    f"after {self.effective_recovery_timeout}s recovery window; worker paused."
                                )
                            },
                        )
                    except Exception:
                        pass
                    raise

            # --------------------------------------------------
            # 5. Build successful result
            # --------------------------------------------------

            result = ProcessingResult(
                upload_id=job.upload_id,
                filename=job.filename,
                file_path=job.file_path,
                file_extension=job.file_extension,
                relative_path=job.relative_path,
                source_folder=job.source_folder,
                folder_chain=job.folder_chain,
                folder_depth=job.folder_depth,
                is_root_level=job.is_root_level,
                status="completed",
                text=normalized_text,
                resume_data=resume_data,
                error=None,
            )

            # --------------------------------------------------
            # 6. Save to existing in-memory ResultStore
            #
            # This keeps the existing result API working.
            # --------------------------------------------------

            result_store.save(
                result
            )

            # --------------------------------------------------
            # 7. Check cancellation again before database writes
            # --------------------------------------------------

            if await batch_repository.is_cancelled_or_expired(job.upload_id):
                logger.info(
                    "Batch '%s' was cancelled during processing. Aborting persistence for %s.",
                    job.upload_id,
                    job.filename,
                )
                return ProcessingResult(
                    upload_id=job.upload_id,
                    filename=job.filename,
                    file_path=job.file_path,
                    file_extension=job.file_extension,
                    relative_path=job.relative_path,
                    source_folder=job.source_folder,
                    folder_chain=job.folder_chain,
                    folder_depth=job.folder_depth,
                    is_root_level=job.is_root_level,
                    status="failed",
                    text=None,
                    resume_data=None,
                    error=f"Batch {job.upload_id} was cancelled during processing.",
                )

            # --------------------------------------------------
            # 8. Save to MongoDB
            #
            # MongoDB now becomes the persistent storage layer.
            # --------------------------------------------------

            await resume_repository.save(
                result
            )

            logger.info(
                "Resume saved to MongoDB successfully: %s",
                job.filename,
            )

            # --------------------------------------------------
            # 9. Generate and save evidence embeddings
            # --------------------------------------------------

            await resume_embedding_generation_service.generate_for_resume(
                upload_id=job.upload_id,
                filename=job.filename,
            )

            logger.info(
                "Resume embeddings generated and saved successfully: %s",
                job.filename,
            )

            # --------------------------------------------------
            # 10. Update batch progress
            # --------------------------------------------------

            await batch_repository.increment_progress(
                batch_id=job.upload_id,
                completed=True,
            )

            logger.info(
                "Resume processed successfully: %s",
                job.filename,
            )

            return result

        except Exception as exc:

            logger.exception(
                "Failed to process resume: %s",
                job.filename,
            )

            # --------------------------------------------------
            # Failed result
            # --------------------------------------------------

            result = ProcessingResult(
                upload_id=job.upload_id,
                filename=job.filename,
                file_path=job.file_path,
                file_extension=job.file_extension,
                relative_path=job.relative_path,
                source_folder=job.source_folder,
                folder_chain=job.folder_chain,
                folder_depth=job.folder_depth,
                is_root_level=job.is_root_level,
                status="failed",
                text=None,
                resume_data=None,
                error=str(exc),
            )

            # --------------------------------------------------
            # Save failed result to ResultStore
            # --------------------------------------------------

            result_store.save(
                result
            )

            # --------------------------------------------------
            # Save failed result to MongoDB
            #
            # This preserves processing status and error
            # information for the upload.
            # --------------------------------------------------

            try:

                await resume_repository.save(
                    result
                )

                logger.info(
                    "Failed resume result saved to MongoDB: %s",
                    job.filename,
                )

            except Exception:

                logger.exception(
                    "Could not save failed resume to MongoDB: %s",
                    job.filename,
                )

            # --------------------------------------------------
            # Clean up any stale or invalid embeddings
            # --------------------------------------------------

            try:

                await resume_embedding_repository.delete(
                    upload_id=job.upload_id,
                    filename=job.filename,
                )

            except Exception:

                logger.exception(
                    "Could not delete stale embeddings for failed resume: %s",
                    job.filename,
                )

            # --------------------------------------------------
            # Update batch progress with failure
            # --------------------------------------------------

            try:
                await batch_repository.increment_progress(
                    batch_id=job.upload_id,
                    completed=False,
                )
            except Exception:
                logger.exception(
                    "Could not update batch progress for failed resume: %s",
                    job.filename,
                )

            return result

    async def run_once(
        self,
    ) -> ProcessingResult:

        job = await local_queue.dequeue()

        try:

            return await self.process_job(
                job
            )

        finally:

            local_queue.task_done()

    async def run_forever(
        self,
    ) -> None:

        logger.info(
            "Resume worker started."
        )

        while True:

            # If Ollama was marked unavailable, pause queue consumption until it recovers
            if not self._ollama_available:
                logger.warning(
                    "Ollama service is unavailable. Pausing worker queue consumption until Ollama recovers..."
                )
                await self._pause_until_ollama_healthy()
                logger.info(
                    "Ollama service recovered. Resuming worker queue processing."
                )

            job = await local_queue.dequeue()

            try:

                await self.process_job(
                    job
                )

            except Exception:

                logger.exception(
                    "Unexpected worker error for: %s",
                    job.filename,
                )

            finally:

                local_queue.task_done()


resume_worker = ResumeWorker()


_worker_task: asyncio.Task | None = None


async def start_worker() -> None:
    """
    Start the background resume worker.
    """

    global _worker_task

    if (
        _worker_task is not None
        and not _worker_task.done()
    ):
        return

    _worker_task = asyncio.create_task(
        resume_worker.run_forever()
    )

    logger.info(
        "Resume worker background task created."
    )


async def stop_worker() -> None:
    """
    Stop the background resume worker.
    """

    global _worker_task

    if _worker_task is None:
        return

    _worker_task.cancel()

    try:

        await _worker_task

    except asyncio.CancelledError:
        pass

    finally:

        _worker_task = None

    logger.info(
        "Resume worker stopped."
    )
