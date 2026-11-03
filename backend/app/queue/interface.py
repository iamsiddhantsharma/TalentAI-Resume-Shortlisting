from abc import ABC, abstractmethod

from app.schemas.processing_job import ProcessingJob


class QueueInterface(ABC):
    """
    Abstract interface for the processing queue.
    """

    @abstractmethod
    async def enqueue(
        self,
        job: ProcessingJob,
    ) -> None:
        """
        Add a processing job.
        """
        raise NotImplementedError

    @abstractmethod
    async def dequeue(self) -> ProcessingJob:
        """
        Get the next processing job.
        """
        raise NotImplementedError

    @abstractmethod
    def size(self) -> int:
        """
        Return current queue size.
        """
        raise NotImplementedError
