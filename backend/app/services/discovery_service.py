from pathlib import Path

from app.schemas.discovered_file import DiscoveredFile


class DiscoveryService:
    """
    Recursively discovers supported resume files from
    an extracted directory.

    This service does not parse or read resume contents.
    It only identifies files and preserves their
    directory provenance.
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".docx",
        ".txt",
    }

    def discover_files(
        self,
        extraction_directory: str,
    ) -> list[DiscoveredFile]:
        """
        Recursively discover supported resume files.

        Parameters
        ----------
        extraction_directory:
            Root directory containing extracted files.

        Returns
        -------
        list[DiscoveredFile]
            All supported resume files discovered recursively.
        """

        root = Path(extraction_directory)

        # --------------------------------------------------
        # Validate extraction directory
        # --------------------------------------------------

        if not root.exists():
            raise FileNotFoundError(
                f"Extraction directory does not exist: {root}"
            )

        if not root.is_dir():
            raise NotADirectoryError(
                f"Extraction path is not a directory: {root}"
            )

        discovered_files: list[DiscoveredFile] = []

        # --------------------------------------------------
        # Recursively scan every item
        # --------------------------------------------------

        for path in root.rglob("*"):

            # We only care about actual files.
            if not path.is_file():
                continue

            # --------------------------------------------------
            # Normalize extension
            # --------------------------------------------------

            extension = path.suffix.lower()

            # --------------------------------------------------
            # Ignore unsupported files
            # --------------------------------------------------

            if extension not in self.SUPPORTED_EXTENSIONS:
                continue

            # --------------------------------------------------
            # Calculate relative path
            # --------------------------------------------------

            relative_path = path.relative_to(root)

            # --------------------------------------------------
            # Determine folder hierarchy
            # --------------------------------------------------

            parent_relative_path = relative_path.parent

            if str(parent_relative_path) == ".":
                folder_chain: list[str] = []
                source_folder = None
                folder_depth = 0
                is_root_level = True

            else:
                folder_chain = list(
                    parent_relative_path.parts
                )

                source_folder = "/".join(
                    folder_chain
                )

                folder_depth = len(
                    folder_chain
                )

                is_root_level = False

            # --------------------------------------------------
            # Create structured discovery object
            # --------------------------------------------------

            discovered_file = DiscoveredFile(
                filename=path.name,
                file_path=str(path),
                relative_path=relative_path.as_posix(),
                file_extension=extension,
                source_folder=source_folder,
                folder_chain=folder_chain,
                folder_depth=folder_depth,
                is_root_level=is_root_level,
            )

            discovered_files.append(
                discovered_file
            )

        return discovered_files


discovery_service = DiscoveryService()
