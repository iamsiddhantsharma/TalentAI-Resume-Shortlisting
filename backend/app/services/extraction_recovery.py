from pydantic import ValidationError

from app.prompts.job_description import (
    JOB_DESCRIPTION_PROMPT,
)

from app.prompts.resume import (
    RESUME_PROMPT,
)

from app.schemas.job_description_object import (
    JobDescriptionObject,
)

from app.schemas.resume_object import (
    ResumeObject,
)

from app.services.extraction_validator import (
    extraction_validator,
)

from app.services.llm_service import (
    llm_service,
)


class ExtractionRecoveryService:
    """
    Handles LLM extraction, Pydantic validation,
    and controlled correction retries.

    Maximum of three attempts are allowed.
    """

    MAX_ATTEMPTS = 3

    # ==================================================
    # CORRECTION PROMPT
    # ==================================================

    def _build_correction_prompt(
        self,
        original_prompt: str,
        invalid_data: dict,
        validation_error: str,
    ) -> str:
        """
        Build a correction prompt containing
        the validation error and previous response.
        """

        return f"""
Your previous response did not match the required
TalentAI structured schema.

VALIDATION ERROR:

{validation_error}

PREVIOUS RESPONSE:

{invalid_data}

Correct the response.

IMPORTANT RULES:

1. Follow the required schema exactly.
2. Use ONLY fields defined by the schema.
3. Do not invent information.
4. Return the COMPLETE corrected JSON object.
5. Return ONLY valid JSON.
6. Do not include markdown.
7. Do not include explanations.
8. Do not add additional fields.
9. Preserve valid information from the previous response.

ORIGINAL EXTRACTION INSTRUCTIONS:

{original_prompt}
"""

    # ==================================================
    # RESUME EXTRACTION
    # ==================================================

    async def extract_resume(
        self,
        resume_text: str,
    ) -> ResumeObject:
        """
        Extract and validate a resume.
        """

        if not resume_text.strip():

            raise ValueError(
                "Resume text cannot be empty."
            )

        original_prompt = RESUME_PROMPT.format(
            resume_text=resume_text
        )

        prompt = original_prompt

        last_error: str | None = None

        for attempt in range(
            1,
            self.MAX_ATTEMPTS + 1,
        ):

            try:

                data = (
                    await llm_service.generate_json(
                        prompt=prompt,
                        schema=ResumeObject,
                    )
                )

                return (
                    extraction_validator
                    .validate_resume(
                        data
                    )
                )

            except ValidationError as exc:

                last_error = str(exc)

                if (
                    attempt
                    == self.MAX_ATTEMPTS
                ):
                    break

                prompt = (
                    self._build_correction_prompt(
                        original_prompt=original_prompt,
                        invalid_data=data,
                        validation_error=last_error,
                    )
                )

            except ValueError as exc:

                last_error = str(exc)

                if (
                    attempt
                    == self.MAX_ATTEMPTS
                ):
                    break

                prompt = (
                    self._build_correction_prompt(
                        original_prompt=original_prompt,
                        invalid_data={},
                        validation_error=last_error,
                    )
                )

        raise ValueError(
            "Resume extraction failed after "
            f"{self.MAX_ATTEMPTS} attempts. "
            f"Last error: {last_error}"
        )

    # ==================================================
    # JOB DESCRIPTION EXTRACTION
    # ==================================================

    async def extract_job_description(
        self,
        job_description_text: str,
    ) -> JobDescriptionObject:
        """
        Extract and validate a Job Description.

        Only extracts:

        - required skills
        - overall experience
        """

        if not job_description_text.strip():

            raise ValueError(
                "Job description text cannot be empty."
            )

        original_prompt = (
            JOB_DESCRIPTION_PROMPT.format(
                job_description_text=(
                    job_description_text
                )
            )
        )

        prompt = original_prompt

        last_error: str | None = None

        for attempt in range(
            1,
            self.MAX_ATTEMPTS + 1,
        ):

            try:

                print(
                    "\n========================================"
                )

                print(
                    f"JOB DESCRIPTION EXTRACTION "
                    f"ATTEMPT {attempt}/{self.MAX_ATTEMPTS}"
                )

                print(
                    "Calling Qwen through Ollama..."
                )

                # ------------------------------------------
                # Call Qwen
                # ------------------------------------------

                data = (
                    await llm_service.generate_json(
                        prompt=prompt,
                        schema=JobDescriptionObject,
                    )
                )

                print(
                    "Qwen response received."
                )

                # ------------------------------------------
                # Validate
                # ------------------------------------------

                validated_data = (
                    extraction_validator
                    .validate_job_description(
                        data
                    )
                )

                print(
                    "Job Description validation successful."
                )

                return validated_data

            except ValidationError as exc:

                last_error = str(exc)

                print(
                    "Validation error:"
                )

                print(
                    last_error
                )

                if (
                    attempt
                    == self.MAX_ATTEMPTS
                ):
                    break

                prompt = (
                    self._build_correction_prompt(
                        original_prompt=original_prompt,
                        invalid_data=data,
                        validation_error=last_error,
                    )
                )

            except ValueError as exc:

                last_error = str(exc)

                print(
                    "Extraction error:"
                )

                print(
                    last_error
                )

                if (
                    attempt
                    == self.MAX_ATTEMPTS
                ):
                    break

                prompt = (
                    self._build_correction_prompt(
                        original_prompt=original_prompt,
                        invalid_data={},
                        validation_error=last_error,
                    )
                )

        raise ValueError(
            "Job description extraction failed after "
            f"{self.MAX_ATTEMPTS} attempts. "
            f"Last error: {last_error}"
        )


extraction_recovery_service = (
    ExtractionRecoveryService()
)
