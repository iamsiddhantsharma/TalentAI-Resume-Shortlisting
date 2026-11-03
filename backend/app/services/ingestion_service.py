from pathlib import Path

from app.queue.local_queue import local_queue
from app.schemas.discovered_file import DiscoveredFile
from app.schemas.processing_job import ProcessingJob


class IngestionService:
    """
    Converts discovered/direct files into ProcessingJob
    objects and places them into the processing queue.
    """

    async def ingest_discovered_file(
        self,
        upload_id: str,
        discovered_file: DiscoveredFile,
    ) -> ProcessingJob:
        """
        Convert a discovered ZIP resume into a processing job.
        """

        job = ProcessingJob(
            upload_id=upload_id,
            filename=discovered_file.filename,
            file_path=discovered_file.file_path,
            file_extension=discovered_file.file_extension,
            relative_path=discovered_file.relative_path,
            source_folder=discovered_file.source_folder,
            folder_chain=discovered_file.folder_chain,
            folder_depth=discovered_file.folder_depth,
            is_root_level=discovered_file.is_root_level,
        )

        await local_queue.enqueue(job)

        return job

    async def ingest_direct_file(
        self,
        upload_id: str,
        file_path: str,
        filename: str | None = None,
    ) -> ProcessingJob:
        """
        Convert a directly uploaded resume into a job.

        Direct files do not have ZIP folder provenance.
        """

        path = Path(file_path)

        actual_filename = (
            filename
            if filename
            else path.name
        )

        extension = path.suffix.lower()

        job = ProcessingJob(
            upload_id=upload_id,
            filename=actual_filename,
            file_path=str(path),
            file_extension=extension,
            relative_path=actual_filename,
            source_folder=None,
            folder_chain=[],
            folder_depth=0,
            is_root_level=True,
        )

        await local_queue.enqueue(job)

        return job


ingestion_service = IngestionService()
