"""
TalentAI — AI Model On-Demand Lifecycle Manager

Manages the execution lifecycle of the local Ollama LLM service:
1. Starts Ollama on demand when an AI ranking or extraction task arrives.
2. Tracks queued and active jobs reliably to prevent premature shutdowns.
3. Enforces a configurable idle grace period (default 5 minutes / 300s).
4. Cancels pending shutdown countdowns immediately when new work arrives.
5. Never interrupts or stops Ollama while any job is active or queued.
6. Handles process failures, startup timeouts, and graceful shutdown cleanly.
"""

import asyncio
from datetime import datetime, timezone
import logging
import shlex
import subprocess
import sys
from typing import Any

from app.config.settings import settings
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class AIModelStatus:
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    STOPPING = "stopping"


class AILifecycleManager:
    """
    Dedicated controller for the local Ollama AI model service.
    """

    def __init__(self) -> None:
        self._status: str = AIModelStatus.STOPPED
        self._active_jobs: set[str] = set()
        self._queued_jobs: set[str] = set()
        self._lock = asyncio.Lock()
        self._subprocess: asyncio.subprocess.Process | None = None
        self._idle_timer_task: asyncio.Task | None = None
        self._last_active_time: datetime | None = None
        self._shutdown_deadline: float | None = None

    @property
    def status(self) -> str:
        return self._status

    @property
    def active_jobs_count(self) -> int:
        return len(self._active_jobs)

    @property
    def queued_jobs_count(self) -> int:
        return len(self._queued_jobs)

    def is_work_in_progress(self) -> bool:
        return bool(self._active_jobs or self._queued_jobs)

    # =========================================================================
    # JOB REGISTRATION & ACQUISITION
    # =========================================================================

    async def register_queued_job(self, job_id: str) -> None:
        """
        Register that an AI job has been queued.
        Immediately cancels any pending idle shutdown timer so the model
        remains available or ready to process incoming work.
        """
        async with self._lock:
            self._queued_jobs.add(job_id)
            self._cancel_idle_timer(reason=f"Queued job '{job_id}' registered")
            logger.info(
                "Registered queued AI job '%s'. Active: %d, Queued: %d",
                job_id,
                len(self._active_jobs),
                len(self._queued_jobs),
            )

    async def acquire_ai_service(self, job_id: str, context: str = "") -> bool:
        """
        Acquire the AI model service for an executing job.
        Transitions the job from queued to active, cancels idle shutdown,
        and ensures Ollama is started and responsive before proceeding.
        """
        async with self._lock:
            # Move from queued to active
            self._queued_jobs.discard(job_id)
            self._active_jobs.add(job_id)
            self._cancel_idle_timer(reason=f"Job '{job_id}' started execution")

            logger.info(
                "Acquiring AI service for job '%s' (context: %s). Active: %d, Queued: %d",
                job_id,
                context or "unspecified",
                len(self._active_jobs),
                len(self._queued_jobs),
            )

            # Ensure Ollama service is up and responsive
            healthy = await self._ensure_ollama_started()
            if not healthy:
                self._active_jobs.discard(job_id)
                raise RuntimeError(
                    f"Failed to acquire AI service: Ollama is unreachable at {settings.OLLAMA_BASE_URL}."
                )

            self._status = AIModelStatus.RUNNING
            return True

    async def release_ai_service(self, job_id: str) -> None:
        """
        Release the AI model service after job completion or failure.
        When all active and queued jobs finish, starts the configurable
        idle grace period before shutting down the model.
        """
        async with self._lock:
            self._active_jobs.discard(job_id)
            self._queued_jobs.discard(job_id)
            self._last_active_time = datetime.now(timezone.utc)

            logger.info(
                "Released AI service for job '%s'. Remaining Active: %d, Queued: %d",
                job_id,
                len(self._active_jobs),
                len(self._queued_jobs),
            )

            # If no more active or queued jobs, schedule idle grace period
            if not self.is_work_in_progress():
                self._status = AIModelStatus.IDLE
                self._schedule_idle_shutdown()

    async def cancel_job(self, job_id: str) -> None:
        """Safely deregister a cancelled job."""
        await self.release_ai_service(job_id)

    # =========================================================================
    # OLLAMA PROCESS MANAGEMENT
    # =========================================================================

    async def _is_ollama_healthy(self) -> bool:
        """Check if Ollama is currently responding via lightweight ping."""
        return await llm_service.check_health()

    async def _ensure_ollama_started(self) -> bool:
        """
        Verify that Ollama is responding. If not, and auto-lifecycle is enabled,
        spawn the local Ollama process and poll for health until ready.
        """
        if await self._is_ollama_healthy():
            self._status = AIModelStatus.RUNNING
            return True

        if not getattr(settings, "OLLAMA_AUTO_LIFECYCLE", True):
            logger.warning(
                "Ollama is unreachable at %s and OLLAMA_AUTO_LIFECYCLE is disabled.",
                settings.OLLAMA_BASE_URL,
            )
            return False

        logger.info("Ollama is not running. Launching on-demand service...")
        self._status = AIModelStatus.STARTING

        command = getattr(settings, "OLLAMA_COMMAND", "ollama serve")
        cmd_args = shlex.split(command, posix=(sys.platform != "win32"))

        try:
            # Spawn Ollama as asynchronous subprocess
            self._subprocess = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            logger.info("Spawned Ollama process PID: %s", self._subprocess.pid)
        except Exception as exc:
            logger.error("Failed to spawn Ollama command '%s': %s", command, exc)
            self._status = AIModelStatus.STOPPED
            return False

        # Wait for service to become responsive
        timeout = getattr(settings, "OLLAMA_STARTUP_TIMEOUT_SECONDS", 60.0)
        poll_interval = 1.0
        elapsed = 0.0

        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            # Check if subprocess died prematurely
            if self._subprocess and self._subprocess.returncode is not None:
                logger.error(
                    "Ollama process exited prematurely with return code %s",
                    self._subprocess.returncode,
                )
                self._status = AIModelStatus.STOPPED
                self._subprocess = None
                return False

            if await self._is_ollama_healthy():
                logger.info("Ollama service successfully started and verified responsive (took %.1fs).", elapsed)
                self._status = AIModelStatus.RUNNING
                return True

        logger.error("Ollama service failed to become healthy within %.1fs timeout.", timeout)
        await self.stop_ollama(force=True)
        return False

    # =========================================================================
    # IDLE SHUTDOWN GRACE PERIOD
    # =========================================================================

    def _cancel_idle_timer(self, reason: str = "") -> None:
        """Cancel pending idle shutdown timer if active."""
        if self._idle_timer_task and not self._idle_timer_task.done():
            self._idle_timer_task.cancel()
            self._idle_timer_task = None
            self._shutdown_deadline = None
            logger.info("Cancelled pending idle shutdown timer: %s", reason or "New work arrived")

    def _schedule_idle_shutdown(self) -> None:
        """Schedule a shutdown after the idle grace period."""
        self._cancel_idle_timer(reason="Rescheduling idle countdown")
        idle_seconds = getattr(settings, "OLLAMA_IDLE_TIMEOUT_SECONDS", 300)

        loop = asyncio.get_event_loop()
        self._shutdown_deadline = loop.time() + idle_seconds
        self._idle_timer_task = asyncio.create_task(
            self._idle_shutdown_worker(idle_seconds)
        )
        logger.info(
            "Scheduled AI model idle shutdown in %d seconds (deadline at %.1f).",
            idle_seconds,
            self._shutdown_deadline,
        )

    async def _idle_shutdown_worker(self, idle_seconds: int) -> None:
        """
        Background task that waits for the idle grace period to elapse.
        If cancelled before expiry, shuts down cleanly without stopping Ollama.
        """
        try:
            await asyncio.sleep(idle_seconds)
        except asyncio.CancelledError:
            logger.debug("Idle shutdown worker cancelled before expiry.")
            return

        async with self._lock:
            # Re-check: if any work arrived, do NOT stop
            if self.is_work_in_progress():
                logger.info(
                    "Idle grace period elapsed, but work is active/queued (%d active, %d queued). Aborting shutdown.",
                    len(self._active_jobs),
                    len(self._queued_jobs),
                )
                return

            logger.info("Idle grace period (%ds) elapsed with zero active or queued jobs. Shutting down Ollama...", idle_seconds)
            await self.stop_ollama(force=False)

    # =========================================================================
    # GRACEFUL SHUTDOWN
    # =========================================================================

    async def stop_ollama(self, force: bool = False) -> bool:
        """
        Gracefully stop the Ollama subprocess.
        Guarantees that Ollama is NEVER stopped while active or queued jobs exist,
        unless force=True is passed (e.g. during application exit).
        """
        if not force and self.is_work_in_progress():
            logger.warning(
                "Refusing to stop Ollama: %d active jobs and %d queued jobs remain.",
                len(self._active_jobs),
                len(self._queued_jobs),
            )
            return False

        self._cancel_idle_timer(reason="Service stopping")
        self._status = AIModelStatus.STOPPING

        if self._subprocess and self._subprocess.returncode is None:
            logger.info("Terminating Ollama subprocess PID: %s...", self._subprocess.pid)
            try:
                self._subprocess.terminate()
                try:
                    await asyncio.wait_for(self._subprocess.wait(), timeout=10.0)
                    logger.info("Ollama subprocess terminated gracefully.")
                except asyncio.TimeoutError:
                    logger.warning("Ollama subprocess did not exit within 10s. Forcing kill...")
                    self._subprocess.kill()
                    await self._subprocess.wait()
                    logger.info("Ollama subprocess killed.")
            except Exception as e:
                logger.error("Error stopping Ollama subprocess: %s", e)
            finally:
                self._subprocess = None

        self._status = AIModelStatus.STOPPED
        logger.info("Ollama AI lifecycle manager status is now STOPPED.")
        return True

    # =========================================================================
    # DIAGNOSTICS & STATUS
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """Return real-time diagnostic status of the AI model lifecycle."""
        loop_time = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0.0
        seconds_remaining = 0.0
        if self._shutdown_deadline and self._shutdown_deadline > loop_time:
            seconds_remaining = max(0.0, self._shutdown_deadline - loop_time)

        return {
            "status": self._status,
            "active_jobs": list(self._active_jobs),
            "queued_jobs": list(self._queued_jobs),
            "active_count": len(self._active_jobs),
            "queued_count": len(self._queued_jobs),
            "is_idle": self._status == AIModelStatus.IDLE,
            "idle_seconds_remaining": round(seconds_remaining, 1),
            "subprocess_pid": self._subprocess.pid if self._subprocess else None,
            "last_active_at": self._last_active_time.isoformat() if self._last_active_time else None,
        }


# Global singleton instance
ai_lifecycle_manager = AILifecycleManager()
