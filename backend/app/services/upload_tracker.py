class UploadTracker:
    """
    Tracks the number of files belonging to each upload.

    This is an in-memory Phase 2 implementation.
    Later this information can be stored in a database.
    """

    def __init__(self) -> None:
        self._totals: dict[str, int] = {}

    def register(
        self,
        upload_id: str,
        total_files: int,
    ) -> None:
        """
        Register the expected number of files
        for an upload.
        """

        self._totals[upload_id] = total_files

    def get_total(
        self,
        upload_id: str,
    ) -> int:
        """
        Return the expected number of files
        for an upload.
        """

        return self._totals.get(
            upload_id,
            0,
        )

    def clear(self) -> None:
        """
        Clear all tracked uploads.
        """

        self._totals.clear()


upload_tracker = UploadTracker()
