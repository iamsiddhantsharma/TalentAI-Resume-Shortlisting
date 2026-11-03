from pathlib import Path
from zipfile import BadZipFile, ZipFile

import anyio

from app.config.settings import settings


from app.utils.file_utils import safe_rmtree


class ZipExtractionError(Exception):
    """
    Raised when a ZIP file cannot be safely extracted.
    """

    pass


class ZipService:

    def _validate_member_path(
        self,
        extraction_directory: Path,
        member_name: str,
    ) -> Path:
        """
        Validate that a ZIP member will be extracted inside
        the intended extraction directory.

        This protects against Zip Slip/path traversal attacks.
        """

        # Convert ZIP paths to the operating system's path format.
        normalized_name = member_name.replace("\\", "/")

        member_path = Path(normalized_name)

        # Reject absolute paths.
        if member_path.is_absolute():
            raise ZipExtractionError(
                f"Unsafe absolute path in ZIP: {member_name}"
            )

        # Build the final extraction path.
        target_path = (
            extraction_directory / member_path
        ).resolve()

        extraction_root = (
            extraction_directory.resolve()
        )

        # Make sure the target remains inside extraction_root.
        try:
            target_path.relative_to(extraction_root)
        except ValueError:
            raise ZipExtractionError(
                f"Unsafe path traversal detected: {member_name}"
            )

        return target_path

    def _extract_zip_sync(
        self,
        zip_path: Path,
        extraction_directory: Path,
    ) -> None:
        """
        Perform ZIP validation and extraction with comprehensive ZIP bomb protection:
        1. Checks archive integrity via testzip().
        2. Enforces maximum archive member count.
        3. Enforces maximum total declared uncompressed size.
        4. Enforces maximum compression ratio threshold.
        5. Validates every entry for Zip Slip / path traversal.
        6. Guards cumulative extracted bytes during streaming decompression.
        """

        try:
            with ZipFile(zip_path, "r") as zip_file:

                # 1. Integrity check
                if zip_file.testzip() is not None:
                    raise ZipExtractionError(
                        "ZIP archive is corrupted."
                    )

                members = zip_file.infolist()

                # 2. Member count enforcement
                if len(members) > settings.MAX_ZIP_MEMBERS_COUNT:
                    raise ZipExtractionError(
                        f"ZIP archive contains {len(members)} entries, exceeding the maximum allowed limit of {settings.MAX_ZIP_MEMBERS_COUNT}."
                    )

                # 3. Pre-extraction declared uncompressed size enforcement
                total_uncompressed = sum(m.file_size for m in members if not m.is_dir())
                max_uncompressed_bytes = settings.MAX_ZIP_UNCOMPRESSED_SIZE_MB * 1024 * 1024
                if total_uncompressed > max_uncompressed_bytes:
                    raise ZipExtractionError(
                        f"ZIP uncompressed size ({total_uncompressed / (1024*1024):.1f}MB) exceeds the maximum allowed limit of {settings.MAX_ZIP_UNCOMPRESSED_SIZE_MB}MB."
                    )

                # 4. Compression ratio threshold enforcement (decompression bomb defense)
                compressed_file_size = zip_path.stat().st_size
                if compressed_file_size > 0:
                    compression_ratio = total_uncompressed / compressed_file_size
                    if compression_ratio > settings.MAX_ZIP_COMPRESSION_RATIO:
                        raise ZipExtractionError(
                            f"Suspicious compression ratio ({compression_ratio:.1f}:1) exceeds the safety threshold of {settings.MAX_ZIP_COMPRESSION_RATIO}:1 (potential ZIP bomb)."
                        )

                # 5. Extract with Zip Slip protection and cumulative byte counter
                cumulative_extracted_bytes = 0

                for member in members:

                    # Validate every path before extracting (Zip Slip protection).
                    target_path = self._validate_member_path(
                        extraction_directory,
                        member.filename,
                    )

                    # Directory entry (preserves folder hierarchy / provenance).
                    if member.is_dir():
                        target_path.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        continue

                    # Create parent directory.
                    target_path.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    # Extract file chunk-by-chunk and monitor uncompressed byte limit
                    with (
                        zip_file.open(member, "r")
                        as source,
                        target_path.open("wb") as destination
                    ):
                        while True:
                            chunk = source.read(1024 * 1024)

                            if not chunk:
                                break

                            cumulative_extracted_bytes += len(chunk)
                            if cumulative_extracted_bytes > max_uncompressed_bytes:
                                raise ZipExtractionError(
                                    f"ZIP extraction exceeded the maximum uncompressed size of {settings.MAX_ZIP_UNCOMPRESSED_SIZE_MB}MB during decompression."
                                )

                            destination.write(chunk)

        except BadZipFile as exc:
            raise ZipExtractionError(
                "The uploaded file is not a valid ZIP archive."
            ) from exc

    async def extract_zip(
        self,
        zip_path: str,
        upload_id: str,
    ) -> str:
        """
        Safely extract a ZIP archive for one upload.

        Returns the extraction directory.
        Cleans up extraction directory on failure.
        """

        source = Path(zip_path)

        if not source.exists():
            raise ZipExtractionError(
                f"ZIP file does not exist: {source}"
            )

        extraction_directory = (
            Path(settings.EXTRACTED_DIR) / upload_id
        )

        extraction_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            await anyio.to_thread.run_sync(
                self._extract_zip_sync,
                source,
                extraction_directory,
            )

        except Exception:
            # Remove partially extracted data if extraction fails.
            if extraction_directory.exists():
                safe_rmtree(extraction_directory)

            raise

        return str(extraction_directory)


zip_service = ZipService()
