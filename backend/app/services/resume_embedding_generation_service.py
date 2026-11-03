from app.database.resume_embedding_repository import (
    resume_embedding_repository,
)
from app.database.resume_repository import resume_repository

from app.schemas.processing_result import ProcessingResult

from app.services.evidence_service import evidence_service
from app.services.evidence_embedding_service import (
    evidence_embedding_service,
)


class ResumeEmbeddingGenerationService:
    """
    Generates and stores evidence-level embeddings for a
    stored Resume.

    Pipeline:

        Stored Resume
            ↓
        Resume structured data
            ↓
        EvidenceService
            ↓
        EvidenceEmbeddingService
            ↓
        BGE embeddings
            ↓
        MongoDB
    """

    async def generate_for_resume(
        self,
        upload_id: str,
        filename: str,
    ) -> dict:
        """
        Generate and persist embeddings for one resume.

        Parameters
        ----------
        upload_id:
            Upload ID of the stored resume.
        filename:
            Filename of the stored resume.

        Returns
        -------
        dict
            Information about generated embeddings.
        """

        # ---------------------------------------------------------
        # 1. Load resume from MongoDB
        # ---------------------------------------------------------

        resume_document = await resume_repository.get(
            upload_id=upload_id,
            filename=filename,
        )

        if resume_document is None:
            raise ValueError(
                f"Resume not found for "
                f"upload_id='{upload_id}', "
                f"filename='{filename}'."
            )

        # ---------------------------------------------------------
        # 2. Validate stored resume
        # ---------------------------------------------------------

        try:
            # MongoDB documents include `_id` (set by the repository).
            # Strip `_id` from a copy before validation so schema
            # changes cannot break this boundary.
            validation_document = dict(resume_document)
            validation_document.pop("_id", None)

            processing_result = ProcessingResult.model_validate(
                validation_document
            )
        except Exception as exc:
            raise ValueError(
                f"Invalid stored resume for "
                f"upload_id='{upload_id}', "
                f"filename='{filename}': {exc}"
            ) from exc

        # ---------------------------------------------------------
        # 3. Check structured data
        # ---------------------------------------------------------

        if processing_result.status != "completed":
            raise ValueError(
                f"Resume '{filename}' has status "
                f"'{processing_result.status}' and cannot be embedded."
            )

        if processing_result.resume_data is None:
            raise ValueError(
                f"Resume '{filename}' "
                f"does not contain structured resume data."
            )

        resume_object = processing_result.resume_data

        # ---------------------------------------------------------
        # 4. Build resume evidence
        # ---------------------------------------------------------

        evidence = evidence_service.build_resume_evidence(
            resume_object
        )

        if not evidence:
            raise ValueError(
                f"Resume '{filename}' "
                f"produced no evidence units."
            )

        # ---------------------------------------------------------
        # 5. Generate BGE embeddings
        # ---------------------------------------------------------

        embedded_evidence = (
            evidence_embedding_service.embed_evidence(
                evidence
            )
        )

        if not embedded_evidence:
            raise ValueError(
                f"Failed to generate embeddings "
                f"for resume '{filename}'."
            )

        # ---------------------------------------------------------
        # 6. Save embeddings to MongoDB
        # ---------------------------------------------------------

        await resume_embedding_repository.save(
            upload_id=upload_id,
            filename=filename,
            embeddings=embedded_evidence,
        )

        # ---------------------------------------------------------
        # 7. Return generation information
        # ---------------------------------------------------------

        return {
            "upload_id": upload_id,
            "filename": filename,
            "evidence_count": len(evidence),
            "embedding_count": len(embedded_evidence),
            "embedding_dimension": len(
                embedded_evidence[0]["embedding"]
            ),
            "status": "completed",
        }


resume_embedding_generation_service = (
    ResumeEmbeddingGenerationService()
)
