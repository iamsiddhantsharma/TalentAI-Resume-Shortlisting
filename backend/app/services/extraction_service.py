from app.prompts.job_description import JOB_DESCRIPTION_PROMPT
from app.prompts.resume import RESUME_PROMPT
from app.schemas.job_description_object import JobDescriptionObject
from app.schemas.resume_object import ResumeObject
from app.services.llm_service import llm_service


class ExtractionService:
    """
    Converts normalized resume and job-description text
    into schema-constrained structured JSON using the LLM.
    """

    # --------------------------------------------------
    # Resume extraction
    # --------------------------------------------------

    async def extract_resume(
        self,
        resume_text: str,
    ) -> dict:
        """
        Extract structured resume information.

        Qwen receives the ResumeObject JSON schema so
        the generated response is constrained to the
        expected structure.
        """

        if not resume_text.strip():
            raise ValueError(
                "Resume text cannot be empty."
            )

        prompt = RESUME_PROMPT.format(
            resume_text=resume_text
        )

        return await llm_service.generate_json(
            prompt=prompt,
            schema=ResumeObject,
        )

    # --------------------------------------------------
    # Job Description extraction
    # --------------------------------------------------

    async def extract_job_description(
        self,
        job_description_text: str,
    ) -> dict:
        """
        Extract structured Job Description information.

        Qwen receives the JobDescriptionObject JSON schema
        so the generated response is constrained to the
        expected structure.
        """

        if not job_description_text.strip():
            raise ValueError(
                "Job description text cannot be empty."
            )

        prompt = JOB_DESCRIPTION_PROMPT.format(
            job_description_text=job_description_text
        )

        return await llm_service.generate_json(
            prompt=prompt,
            schema=JobDescriptionObject,
        )


extraction_service = ExtractionService()
