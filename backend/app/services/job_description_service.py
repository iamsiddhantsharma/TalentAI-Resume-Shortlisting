from pathlib import Path
from uuid import uuid4

from app.parser.parser_factory import (
    parser_factory,
)

from app.schemas.job_description import (
    JobDescription,
)

from app.services.extraction_recovery import (
    extraction_recovery_service,
)

from app.services.text_normalizer import (
    text_normalizer,
)


class JobDescriptionService:
    """
    Handles Job Description input from:

    1. Uploaded PDF/DOCX/TXT
    2. JSON text
    3. Raw plain text

    Pipeline:

        Input
          ↓
        Parser
          ↓
        Text Normalizer
          ↓
        Qwen 3
          ↓
        Pydantic Validation
          ↓
        JobDescriptionObject
          ↓
        JobDescription
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".docx",
        ".txt",
    }

    # ==================================================
    # FILE
    # ==================================================

    async def process_file(
        self,
        file_path: str,
        filename: str,
    ) -> JobDescription:

        path = Path(file_path)

        if not path.exists():

            raise FileNotFoundError(
                f"Job Description file does not exist: {path}"
            )

        if not path.is_file():

            raise FileNotFoundError(
                f"Job Description path is not a file: {path}"
            )

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:

            raise ValueError(
                "Unsupported Job Description file type: "
                f"{extension}"
            )

        # --------------------------------------------------
        # Parse
        # --------------------------------------------------

        parser = (
            parser_factory.get_parser(
                extension
            )
        )

        text = parser.parse(
            str(path)
        )

        # --------------------------------------------------
        # Normalize
        # --------------------------------------------------

        normalized_text = (
            text_normalizer.normalize(
                text
            )
        )

        if not normalized_text.strip():

            raise ValueError(
                "Job Description contains no readable text."
            )

        # --------------------------------------------------
        # Extract
        # --------------------------------------------------

        structured_data = (
            await extraction_recovery_service
            .extract_job_description(
                normalized_text
            )
        )

        # --------------------------------------------------
        # Return
        # --------------------------------------------------

        return JobDescription(
            jd_id=str(uuid4()),
            input_type="file",
            filename=filename,
            file_extension=extension,
            raw_text=normalized_text,
            status="completed",
            structured_data=structured_data,
            error=None,
        )

    # ==================================================
    # JSON TEXT
    # ==================================================

    async def process_text(
        self,
        text: str,
    ) -> JobDescription:

        if not text:

            raise ValueError(
                "Job Description text cannot be empty."
            )

        # --------------------------------------------------
        # Normalize
        # --------------------------------------------------

        normalized_text = (
            text_normalizer.normalize(
                text
            )
        )

        if not normalized_text.strip():

            raise ValueError(
                "Job Description contains no readable text."
            )

        # --------------------------------------------------
        # Extract
        # --------------------------------------------------

        structured_data = (
            await extraction_recovery_service
            .extract_job_description(
                normalized_text
            )
        )

        # --------------------------------------------------
        # Return
        # --------------------------------------------------

        return JobDescription(
            jd_id=str(uuid4()),
            input_type="text",
            filename=None,
            file_extension=None,
            raw_text=normalized_text,
            status="completed",
            structured_data=structured_data,
            error=None,
        )


job_description_service = (
    JobDescriptionService()
)
