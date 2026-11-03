from app.schemas.processing_result import (
    ProcessingResult,
)

from app.schemas.job_description import (
    JobDescription,
)


class ResultStore:
    """
    Temporary in-memory storage for TalentAI processing results.

    Privacy policy:
        All stored resume and Job Description results are temporary.
        They can be cleared when the HR session ends or the application
        shuts down.

    Matching is NOT performed here.
    """

    def __init__(self) -> None:

        # ----------------------------------------------------
        # Resume results
        # ----------------------------------------------------

        self._results: dict[
            str,
            ProcessingResult,
        ] = {}

        # ----------------------------------------------------
        # Job Description results
        # ----------------------------------------------------

        self._job_descriptions: dict[
            str,
            JobDescription,
        ] = {}

    # ========================================================
    # RESUME RESULTS
    # ========================================================

    def _make_resume_key(
        self,
        result: ProcessingResult,
    ) -> str:

        return (
            f"{result.upload_id}:"
            f"{result.filename}"
        )

    def save(
        self,
        result: ProcessingResult,
    ) -> None:

        key = self._make_resume_key(result)

        self._results[key] = result

    def get(
        self,
        upload_id: str,
        filename: str,
    ) -> ProcessingResult | None:

        key = (
            f"{upload_id}:"
            f"{filename}"
        )

        return self._results.get(key)

    def get_all(
        self,
    ) -> list[ProcessingResult]:

        return list(
            self._results.values()
        )

    def get_by_upload(
        self,
        upload_id: str,
    ) -> list[ProcessingResult]:

        return [
            result
            for result in self._results.values()
            if result.upload_id == upload_id
        ]

    def count(
        self,
    ) -> int:

        return len(
            self._results
        )

    # ========================================================
    # JOB DESCRIPTION RESULTS
    # ========================================================

    def save_job_description(
        self,
        job_description: JobDescription,
    ) -> None:
        """
        Store the active Job Description in memory.

        TalentAI supports exactly one JD at a time, so any
        previously stored in-memory JD is replaced.
        """

        self._job_descriptions.clear()

        self._job_descriptions[
            job_description.jd_id
        ] = job_description

    def get_job_description(
        self,
        jd_id: str,
    ) -> JobDescription | None:

        return self._job_descriptions.get(
            jd_id
        )

    def get_all_job_descriptions(
        self,
    ) -> list[JobDescription]:

        return list(
            self._job_descriptions.values()
        )

    def count_job_descriptions(
        self,
    ) -> int:

        return len(
            self._job_descriptions
        )

    # ========================================================
    # PRIVACY CLEANUP
    # ========================================================

    def clear(self) -> None:
        """
        Permanently remove all temporary in-memory
        resume and Job Description results.
        """

        self._results.clear()

        self._job_descriptions.clear()


result_store = ResultStore()
