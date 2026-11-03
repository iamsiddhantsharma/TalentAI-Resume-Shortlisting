from pydantic import ValidationError

from app.schemas.job_description_object import (
    JobDescriptionObject,
)
from app.schemas.resume_object import ResumeObject


class ExtractionValidator:
    """
    Validates structured LLM output against
    TalentAI Pydantic schemas.
    """

    def validate_resume(
        self,
        data: dict,
    ) -> ResumeObject:
        """
        Validate extracted resume JSON.
        """

        try:
            return ResumeObject.model_validate(
                data
            )

        except ValidationError as exc:
            raise ValueError(
                f"Resume validation failed: {exc}"
            ) from exc

    def validate_job_description(
        self,
        data: dict,
    ) -> JobDescriptionObject:
        """
        Validate extracted JD JSON.
        """

        try:
            return JobDescriptionObject.model_validate(
                data
            )

        except ValidationError as exc:
            raise ValueError(
                f"Job description validation failed: {exc}"
            ) from exc


extraction_validator = ExtractionValidator()
