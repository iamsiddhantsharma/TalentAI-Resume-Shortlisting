"""
Synthetic Test Suite: AI Model Lifecycle Manager & HR CLI Validation

Tests:
1. On-demand Ollama startup when job acquires AI service.
2. Active jobs tracking and rejection of shutdown while jobs are active.
3. Queued jobs tracking and rejection of shutdown while jobs are queued.
4. Idle grace period transition when all jobs are released.
5. Immediate cancellation of idle shutdown timer when new work arrives.
6. Automatic idle shutdown after configurable grace period elapses.
7. Job failure cleanup ensuring no orphaned active jobs.
8. Startup failure / timeout handling.
9. HR CLI account creation password validation (min 8 chars, matching confirmation).
"""

import asyncio
from datetime import datetime, timezone
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config.settings import settings
from app.services.ai_lifecycle_manager import AILifecycleManager, AIModelStatus


class TestAILifecycleManager(unittest.IsolatedAsyncioTestCase):
    """Synthetic unit tests for AILifecycleManager."""

    async def asyncSetUp(self):
        # Create a fresh isolated lifecycle manager instance for each test
        self.mgr = AILifecycleManager()

    async def asyncTearDown(self):
        # Clean up any pending timer tasks
        await self.mgr.stop_ollama(force=True)

    async def test_01_acquire_starts_service_and_tracks_active_job(self):
        """Test on-demand acquisition starts Ollama and tracks active job."""
        with patch.object(self.mgr, "_is_ollama_healthy", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True

            acquired = await self.mgr.acquire_ai_service("synthetic-job-001", context="test")
            self.assertTrue(acquired)
            self.assertEqual(self.mgr.status, AIModelStatus.RUNNING)
            self.assertEqual(self.mgr.active_jobs_count, 1)
            self.assertEqual(self.mgr.queued_jobs_count, 0)
            self.assertTrue(self.mgr.is_work_in_progress())

            status = self.mgr.get_status()
            self.assertIn("synthetic-job-001", status["active_jobs"])
            self.assertEqual(status["active_count"], 1)

    async def test_02_register_queued_job_cancels_idle_timer(self):
        """Test registering a queued job tracks queue and prevents idle shutdown."""
        # Set manager in IDLE state with mock idle timer
        self.mgr._status = AIModelStatus.IDLE
        self.mgr._schedule_idle_shutdown()
        self.assertIsNotNone(self.mgr._idle_timer_task)

        # New queued job arrives
        await self.mgr.register_queued_job("synthetic-queued-001")
        self.assertEqual(self.mgr.queued_jobs_count, 1)
        self.assertTrue(self.mgr.is_work_in_progress())
        # Idle timer should now be cancelled
        self.assertIsNone(self.mgr._idle_timer_task)

    async def test_03_active_jobs_prevent_shutdown(self):
        """Test Ollama cannot be stopped while active jobs are executing."""
        with patch.object(self.mgr, "_is_ollama_healthy", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            await self.mgr.acquire_ai_service("active-job-xyz")

            # Non-force stop must be rejected
            stopped = await self.mgr.stop_ollama(force=False)
            self.assertFalse(stopped)
            self.assertEqual(self.mgr.status, AIModelStatus.RUNNING)
            self.assertEqual(self.mgr.active_jobs_count, 1)

    async def test_04_queued_jobs_prevent_shutdown(self):
        """Test Ollama cannot be stopped while queued jobs are waiting."""
        await self.mgr.register_queued_job("queued-job-abc")

        stopped = await self.mgr.stop_ollama(force=False)
        self.assertFalse(stopped)
        self.assertEqual(self.mgr.queued_jobs_count, 1)

    async def test_05_release_triggers_idle_grace_period(self):
        """Test releasing the last job triggers idle grace period countdown."""
        with patch.object(self.mgr, "_is_ollama_healthy", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            await self.mgr.acquire_ai_service("job-to-release")
            self.assertEqual(self.mgr.active_jobs_count, 1)

            # Patch settings to a short idle grace period for testing
            with patch.object(settings, "OLLAMA_IDLE_TIMEOUT_SECONDS", 10):
                await self.mgr.release_ai_service("job-to-release")

                self.assertEqual(self.mgr.active_jobs_count, 0)
                self.assertEqual(self.mgr.status, AIModelStatus.IDLE)
                self.assertIsNotNone(self.mgr._idle_timer_task)
                status = self.mgr.get_status()
                self.assertTrue(status["is_idle"])
                self.assertGreater(status["idle_seconds_remaining"], 0)

    async def test_06_new_work_cancels_pending_idle_shutdown(self):
        """Test new work arriving during idle grace period cancels pending shutdown."""
        with patch.object(self.mgr, "_is_ollama_healthy", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True

            with patch.object(settings, "OLLAMA_IDLE_TIMEOUT_SECONDS", 30):
                await self.mgr.acquire_ai_service("job-phase-1")
                await self.mgr.release_ai_service("job-phase-1")
                self.assertEqual(self.mgr.status, AIModelStatus.IDLE)
                self.assertIsNotNone(self.mgr._idle_timer_task)

                # New work arrives during grace period
                await self.mgr.acquire_ai_service("job-phase-2")
                self.assertIsNone(self.mgr._idle_timer_task)
                self.assertEqual(self.mgr.status, AIModelStatus.RUNNING)
                self.assertEqual(self.mgr.active_jobs_count, 1)

    async def test_07_idle_shutdown_executes_after_grace_period(self):
        """Test manager shuts down Ollama after grace period expires with no jobs."""
        with patch.object(self.mgr, "_is_ollama_healthy", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            with patch.object(self.mgr, "stop_ollama", new_callable=AsyncMock) as mock_stop:
                mock_stop.return_value = True

                # Fast idle timeout (0.05 seconds)
                with patch.object(settings, "OLLAMA_IDLE_TIMEOUT_SECONDS", 0.05):
                    await self.mgr.acquire_ai_service("quick-job")
                    await self.mgr.release_ai_service("quick-job")

                    # Wait for idle timeout worker to complete
                    await asyncio.sleep(0.1)

                    mock_stop.assert_called_once_with(force=False)

    async def test_08_startup_failure_cleans_up_safely(self):
        """Test startup failure raises error and does not leave active job registered."""
        with patch.object(self.mgr, "_is_ollama_healthy", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = False
            with patch.object(self.mgr, "_ensure_ollama_started", new_callable=AsyncMock) as mock_ensure:
                mock_ensure.return_value = False

                with self.assertRaises(RuntimeError) as ctx:
                    await self.mgr.acquire_ai_service("failing-job")

                self.assertIn("Failed to acquire AI service", str(ctx.exception))
                self.assertEqual(self.mgr.active_jobs_count, 0)
                self.assertEqual(self.mgr.status, AIModelStatus.STOPPED)

    async def test_09_job_failure_releases_service_safely(self):
        """Test an exception during job execution still releases service in finally block."""
        with patch.object(self.mgr, "_is_ollama_healthy", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            await self.mgr.acquire_ai_service("crashing-job")
            self.assertEqual(self.mgr.active_jobs_count, 1)

            # Simulate pipeline try...finally block
            try:
                raise ValueError("Simulated ranking failure")
            except ValueError:
                pass
            finally:
                await self.mgr.release_ai_service("crashing-job")

            self.assertEqual(self.mgr.active_jobs_count, 0)
            self.assertEqual(self.mgr.status, AIModelStatus.IDLE)


class TestManageHRCLI(unittest.IsolatedAsyncioTestCase):
    """Synthetic unit tests for HR Management CLI validation."""

    async def test_cli_rejects_short_password(self):
        from app.cli.manage_hr import cmd_create
        args = MagicMock()
        args.username = "hr_test"
        args.email = "hr@test.local"
        args.name = "Test HR"
        args.password = "short"  # < 8 chars

        res = await cmd_create(args)
        self.assertEqual(res, 1)

    async def test_cli_rejects_short_username(self):
        from app.cli.manage_hr import cmd_create
        args = MagicMock()
        args.username = "ab"  # < 3 chars
        args.email = "hr@test.local"
        args.name = "Test HR"
        args.password = "valid_password_123"

        res = await cmd_create(args)
        self.assertEqual(res, 1)


if __name__ == "__main__":
    unittest.main()
