import asyncio

from app.queue.interface import QueueInterface
from app.schemas.processing_job import ProcessingJob


class LocalQueue(QueueInterface):
    """
    Development in-memory queue.

    Later this can be replaced by Redis, RabbitMQ,
    Kafka, etc. without changing the ingestion layer.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[
            ProcessingJob
        ] = asyncio.Queue()

    async def enqueue(
        self,
        job: ProcessingJob,
    ) -> None:
        """
        Add a job to the queue.
        """

        await self._queue.put(job)

    async def dequeue(self) -> ProcessingJob:
        """
        Wait for and return the next job.
        """

        return await self._queue.get()

    def size(self) -> int:
        """
        Return the number of waiting jobs.
        """

        return self._queue.qsize()

    def task_done(self) -> None:
        """
        Mark a dequeued job as completed.
        """

        self._queue.task_done()

    async def join(self) -> None:
        """
        Wait until all queued jobs are completed.
        """

        await self._queue.join()


local_queue = LocalQueue()
resume_queue = local_queue
