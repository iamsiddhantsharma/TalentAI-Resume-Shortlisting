import asyncio
import io
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.config.settings import settings
from app.queue.local_queue import local_queue
from app.queue.worker import ResumeWorker
from app.schemas.processing_job import ProcessingJob
from app.schemas.processing_result import ProcessingResult
from app.schemas.resume_object import ResumeObject
from app.services.llm_service import LLMService, TRANSIENT_EXCEPTIONS


class TestLLMServiceResilience(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for LLMService error diagnostics, transient retries, and context settings.
    """

    async def asyncSetUp(self):
        self.service = LLMService()

    async def test_connection_refusal_retries_and_raises(self):
        """
        Test that transient ConnectError triggers bounded retries with exponential backoff
        and finally re-raises ConnectError.
        """
        payload = {"model": "qwen3:8b", "prompt": "test", "options": {}}

        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")) as mock_post, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            with self.assertRaises(httpx.ConnectError):
                await self.service._send_request(payload)

            # Max retries is 2 -> total attempts = 3
            self.assertEqual(mock_post.call_count, 3)
            # Sleep was called twice (after attempt 1 and attempt 2)
            self.assertEqual(mock_sleep.call_count, 2)
            mock_sleep.assert_any_call(1.0)
            mock_sleep.assert_any_call(2.0)

    async def test_server_disconnection_retries_and_raises(self):
        """
        Test that RemoteProtocolError (server disconnected without response)
        is recognized as transient and retried.
        """
        payload = {"model": "qwen3:8b", "prompt": "test", "options": {}}

        with patch("httpx.AsyncClient.post", side_effect=httpx.RemoteProtocolError("Server disconnected")) as mock_post, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            with self.assertRaises(httpx.RemoteProtocolError):
                await self.service._send_request(payload)

            self.assertEqual(mock_post.call_count, 3)
            self.assertEqual(mock_sleep.call_count, 2)

    async def test_http_500_diagnostic_body_logging_without_pii(self):
        """
        Test that HTTP 500 error response body from Ollama is captured and logged
        without logging candidate PII or the raw prompt.
        """
        payload = {
            "model": "qwen3:8b",
            "prompt": "CONFIDENTIAL RESUME TEXT WITH PII: John Doe, 555-1234",
            "options": {},
        }

        mock_request = httpx.Request("POST", "http://127.0.0.1:11434/api/generate")
        mock_response = httpx.Response(
            status_code=500,
            text='{"error": "model requires 6.2 GiB VRAM but only 5.1 GiB available"}',
            request=mock_request,
        )

        with patch("httpx.AsyncClient.post", return_value=mock_response), \
             self.assertLogs("app.services.llm_service", level="ERROR") as cm:

            with self.assertRaises(httpx.HTTPStatusError) as exc_context:
                await self.service._send_request(payload)

            self.assertEqual(exc_context.exception.response.status_code, 500)

            # Verify log output preserves diagnostic details
            log_output = "\n".join(cm.output)
            self.assertIn("Ollama HTTP error 500", log_output)
            self.assertIn("model requires 6.2 GiB VRAM", log_output)

            # Verify sensitive prompt/PII is NOT in the logs
            self.assertNotIn("CONFIDENTIAL RESUME TEXT", log_output)
            self.assertNotIn("John Doe", log_output)
            self.assertNotIn("555-1234", log_output)

    async def test_request_payload_includes_safe_context_and_predict_options(self):
        """
        Test that generate_json and generate send bounded num_ctx and num_predict options.
        """
        captured_payloads = []

        async def fake_send(payload):
            captured_payloads.append(payload)
            return {"response": '{"name": "Alice", "skills": ["Python"]}'}

        with patch.object(self.service, "_send_request", side_effect=fake_send):
            result = await self.service.generate_json("Extract resume", schema=ResumeObject)

            self.assertEqual(len(captured_payloads), 1)
            opts = captured_payloads[0].get("options", {})
            self.assertEqual(opts.get("num_ctx"), 4096)
            self.assertEqual(opts.get("num_predict"), 1024)
            self.assertEqual(opts.get("temperature"), 0.0)
            self.assertFalse(captured_payloads[0].get("think"))


class TestWorkerResilience(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for ResumeWorker outage recovery, circuit breaker, and batch preservation.
    """

    def setUp(self):
        # Create a worker with fast test timeouts
        self.worker = ResumeWorker(
            recovery_timeout=0.1,
            health_check_interval=0.02,
        )

    def _create_sample_job(self, upload_id: str, filename: str) -> ProcessingJob:
        return ProcessingJob(
            upload_id=upload_id,
            filename=filename,
            file_path="sample.txt",
            file_extension=".txt",
            relative_path=filename,
            source_folder="Engineering",
            folder_chain=["cvs", "Engineering"],
            folder_depth=2,
            is_root_level=False,
        )

    async def test_recovery_after_temporary_outage(self):
        """
        Test that when Ollama fails on initial call but recovers within the recovery window,
        the worker retries the current resume and completes it successfully.
        """
        job = self._create_sample_job("test-batch-rec", "candidate_1.txt")

        # Mock parser and normalizer
        mock_parser = MagicMock()
        mock_parser.parse.return_value = "Candidate John Doe Python Developer"

        # Mock extraction recovery service: 1st call fails with ConnectError, 2nd call succeeds
        mock_resume = ResumeObject(name="John Doe", skills=["Python"])
        extract_mock = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                mock_resume,
            ]
        )

        # Mock health check: 1st returns False, 2nd returns True (recovered)
        health_mock = AsyncMock(side_effect=[False, True])

        with patch("app.queue.worker.parser_factory.get_parser", return_value=mock_parser), \
             patch("app.queue.worker.text_normalizer.normalize", return_value="Candidate John Doe Python Developer"), \
             patch("app.queue.worker.extraction_recovery_service.extract_resume", extract_mock), \
             patch.object(self.worker, "check_ollama_health", health_mock), \
             patch("app.queue.worker.batch_repository.is_cancelled_or_expired", AsyncMock(return_value=False)), \
             patch("app.queue.worker.batch_repository.increment_progress", AsyncMock()) as mock_inc, \
             patch("app.queue.worker.resume_repository.save", AsyncMock()) as mock_save, \
             patch("app.queue.worker.result_store.save", MagicMock()), \
             patch("app.queue.worker.resume_embedding_generation_service.generate_for_resume", AsyncMock()):

            result = await self.worker.process_job(job)

            # Assertions
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.filename, "candidate_1.txt")
            self.assertEqual(result.source_folder, "Engineering")
            self.assertEqual(result.folder_chain, ["cvs", "Engineering"])
            self.assertEqual(result.folder_depth, 2)
            self.assertFalse(result.is_root_level)

            # Extraction was attempted twice (initial + retry)
            self.assertEqual(extract_mock.call_count, 2)

            # Progress incremented with completed=True
            mock_inc.assert_called_once_with(batch_id="test-batch-rec", completed=True)

            # Exactly one resume saved to MongoDB (no duplicates from failed retry)
            self.assertEqual(mock_save.call_count, 1)
            saved_result = mock_save.call_args[0][0]
            self.assertEqual(saved_result.status, "completed")

    async def test_persistent_outage_fails_current_and_pauses_worker(self):
        """
        Test that when Ollama remains unavailable beyond the recovery window,
        the current job fails with a clear infrastructure status and worker marks itself unavailable.
        """
        job = self._create_sample_job("test-batch-persist", "candidate_2.txt")

        mock_parser = MagicMock()
        mock_parser.parse.return_value = "Candidate Jane Doe"

        extract_mock = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        health_mock = AsyncMock(return_value=False)

        with patch("app.queue.worker.parser_factory.get_parser", return_value=mock_parser), \
             patch("app.queue.worker.text_normalizer.normalize", return_value="Candidate Jane Doe"), \
             patch("app.queue.worker.extraction_recovery_service.extract_resume", extract_mock), \
             patch.object(self.worker, "check_ollama_health", health_mock), \
             patch("app.queue.worker.batch_repository.is_cancelled_or_expired", AsyncMock(return_value=False)), \
             patch("app.queue.worker.batch_repository.increment_progress", AsyncMock()) as mock_inc, \
             patch("app.queue.worker.batch_repository.update_status", AsyncMock()) as mock_update_status, \
             patch("app.queue.worker.resume_repository.save", AsyncMock()) as mock_save, \
             patch("app.queue.worker.result_store.save", MagicMock()), \
             patch("app.queue.worker.resume_embedding_repository.delete", AsyncMock()):

            result = await self.worker.process_job(job)

            # Current job is failed
            self.assertEqual(result.status, "failed")
            self.assertIn("Connection refused", result.error)

            # Worker marks Ollama unavailable to pause queue consumption
            self.assertFalse(self.worker._ollama_available)

            # Batch progress incremented with completed=False
            mock_inc.assert_called_once_with(batch_id="test-batch-persist", completed=False)

            # Batch status updated with infrastructure alert metadata
            mock_update_status.assert_called_once()
            call_kwargs = mock_update_status.call_args[1]
            self.assertIn("infrastructure_alert", call_kwargs.get("metadata", {}))

            # Exactly one failed record in MongoDB
            self.assertEqual(mock_save.call_count, 1)

    async def test_temporary_outage_does_not_drain_remaining_batch(self):
        """
        Verify that when Ollama is unavailable, the queue is NOT drained as failed.
        Remaining jobs stay safely in the queue until Ollama is healthy again.
        """
        job1 = self._create_sample_job("batch-drain-test", "resume_1.txt")
        job2 = self._create_sample_job("batch-drain-test", "resume_2.txt")

        # Put both jobs into local_queue
        await local_queue.enqueue(job1)
        await local_queue.enqueue(job2)
        self.assertEqual(local_queue.size(), 2)

        # Worker is currently marked unavailable (from persistent outage on job 1)
        self.worker._ollama_available = False

        # If health check returns False, _pause_until_ollama_healthy keeps waiting
        # Simulate: health check returns False once, then True (Ollama comes back)
        pause_polls = 0
        async def fake_health():
            nonlocal pause_polls
            pause_polls += 1
            return pause_polls >= 2

        with patch.object(self.worker, "check_ollama_health", side_effect=fake_health):
            # Pause should wait until poll 2 succeeds
            await self.worker._pause_until_ollama_healthy(poll_interval=0.01)

            # Now Ollama is available again
            self.assertTrue(self.worker._ollama_available)
            self.assertEqual(pause_polls, 2)

            # Verify both jobs are still in queue (NOT drained as failed)
            self.assertEqual(local_queue.size(), 2)

            # Clean queue for next tests
            j1 = await local_queue.dequeue()
            local_queue.task_done()
            j2 = await local_queue.dequeue()
            local_queue.task_done()
            self.assertEqual(local_queue.size(), 0)


if __name__ == "__main__":
    unittest.main()
