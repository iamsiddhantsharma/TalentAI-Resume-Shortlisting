import hashlib
import os
from pathlib import Path
import shutil
import stat
from uuid import uuid4

from fastapi import UploadFile

from app.config.settings import settings
from app.schemas.storage import StoredFile
from app.utils.file_utils import safe_rmtree


class UploadSizeLimitExceeded(Exception):
    """Raised when an uploaded file exceeds the configured maximum size."""
    def __init__(self, message: str, file_name: str, size_bytes: int, max_bytes: int):
        super().__init__(message)
        self.file_name = file_name
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


class StorageService:

    CHUNK_SIZE = 1024 * 1024  # 1 MB

    async def save_file(
        self,
        file: UploadFile,
        upload_id: str,
        max_bytes: int | None = None,
    ) -> StoredFile:
        """
        Save one uploaded file to the upload-specific directory.

        The file is streamed in chunks so that large files do not
        need to be loaded completely into memory.
        Enforces maximum file size limit during streaming.
        """

        if not file.filename:
            raise ValueError(
                "Uploaded file does not have a filename."
            )

        original_filename = Path(
            file.filename
        ).name

        if not original_filename:
            raise ValueError(
                "Invalid filename."
            )

        upload_directory = (
            Path(settings.UPLOAD_DIR)
            / upload_id
        )

        upload_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        original_path = Path(
            original_filename
        )

        extension = (
            original_path.suffix.lower()
        )

        unique_name = (
            f"{original_path.stem}_"
            f"{uuid4().hex[:8]}"
            f"{extension}"
        )

        destination = (
            upload_directory
            / unique_name
        )

        sha256 = hashlib.sha256()
        file_size = 0
        limit_bytes = (
            max_bytes
            if max_bytes is not None
            else settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        )

        try:

            with destination.open(
                "wb"
            ) as output_file:

                while True:

                    chunk = await file.read(
                        self.CHUNK_SIZE
                    )

                    if not chunk:
                        break

                    file_size += len(
                        chunk
                    )

                    if file_size > limit_bytes:
                        raise UploadSizeLimitExceeded(
                            f"File '{original_filename}' exceeds the maximum allowed upload limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                            file_name=original_filename,
                            size_bytes=file_size,
                            max_bytes=limit_bytes,
                        )

                    output_file.write(
                        chunk
                    )

                    sha256.update(
                        chunk
                    )

        except Exception:

            if destination.exists():
                destination.unlink(missing_ok=True)

            raise

        if file_size == 0:

            if destination.exists():
                destination.unlink()

            raise ValueError(
                f"Uploaded file is empty: "
                f"{original_filename}"
            )

        return StoredFile(
            original_filename=original_filename,
            stored_filename=unique_name,
            file_path=str(destination),
            file_size=file_size,
            sha256=sha256.hexdigest(),
            file_extension=extension,
        )

    # ========================================================
    # PRIVACY CLEANUP
    # ========================================================

    def delete_upload(
        self,
        upload_id: str,
    ) -> bool:
        """
        Delete all files belonging to one upload.

        This removes the complete upload-specific directory using safe_rmtree.
        """

        base_upload_dir = Path(settings.UPLOAD_DIR).resolve()
        upload_directory = (base_upload_dir / upload_id).resolve()

        # Strict containment check: cannot delete outside base upload directory
        try:
            upload_directory.relative_to(base_upload_dir)
        except ValueError:
            raise ValueError(f"Path traversal detected: {upload_id}")

        if upload_directory.exists():
            return safe_rmtree(upload_directory)
        return True

    def delete_all_uploads(
        self,
    ) -> None:
        """
        Delete all temporary uploaded files.

        Development/testing and application shutdown cleanup.
        """

        upload_directory = Path(
            settings.UPLOAD_DIR
        ).resolve()

        if upload_directory.exists():

            for item in upload_directory.iterdir():

                try:
                    item.resolve().relative_to(upload_directory)
                except ValueError:
                    continue

                if item.is_dir():

                    safe_rmtree(
                        item
                    )

                elif item.is_file():

                    try:
                        os.chmod(item, stat.S_IWRITE)
                    except Exception:
                        pass
                    item.unlink(missing_ok=True)

    def delete_extracted_files(
        self,
    ) -> None:
        """
        Delete all extracted temporary files.
        """

        extracted_directory = Path(
            settings.EXTRACTED_DIR
        ).resolve()

        if extracted_directory.exists():

            for item in extracted_directory.iterdir():

                try:
                    item.resolve().relative_to(extracted_directory)
                except ValueError:
                    continue

                if item.is_dir():

                    safe_rmtree(
                        item
                    )

                elif item.is_file():

                    try:
                        os.chmod(item, stat.S_IWRITE)
                    except Exception:
                        pass
                    item.unlink(missing_ok=True)

    def delete_failed_files(
        self,
    ) -> None:
        """
        Delete all files associated with failed processing.
        """

        failed_directory = Path(
            settings.FAILED_DIR
        ).resolve()

        if failed_directory.exists():

            for item in failed_directory.iterdir():

                try:
                    item.resolve().relative_to(failed_directory)
                except ValueError:
                    continue

                if item.is_dir():

                    safe_rmtree(
                        item
                    )

                elif item.is_file():

                    try:
                        os.chmod(item, stat.S_IWRITE)
                    except Exception:
                        pass
                    item.unlink(missing_ok=True)

    def clear_temporary_storage(
        self,
    ) -> None:
        """
        Remove all temporary TalentAI filesystem data.
        """

        self.delete_all_uploads()

        self.delete_extracted_files()

        self.delete_failed_files()


storage_service = StorageService()
