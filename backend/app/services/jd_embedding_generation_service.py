from app.database.jd_embedding_repository import (
    jd_embedding_repository,
)
from app.database.jd_repository import jd_repository

from app.schemas.job_description import JobDescription

from app.services.evidence_service import evidence_service
from app.services.evidence_embedding_service import (
    evidence_embedding_service,
)


class JobDescriptionEmbeddingGenerationService:
    """
    Generates and stores evidence-level embeddings for a
    stored Job Description.

    Pipeline:

        Stored JD
            ↓
        JD structured data
            ↓
        EvidenceService
            ↓
        EvidenceEmbeddingService
            ↓
        BGE embeddings
            ↓
        MongoDB
    """

    async def generate_for_jd(
        self,
        jd_id: str,
    ) -> dict:
        """
        Generate and persist embeddings for one JD.

        Parameters
        ----------
        jd_id:
            ID of the stored Job Description.

        Returns
        -------
        dict
            Information about generated embeddings.
        """

        # ---------------------------------------------------------
        # 1. Load JD from MongoDB
        # ---------------------------------------------------------

        jd_document = await jd_repository.get(jd_id)

        if jd_document is None:
            raise ValueError(
                f"Job description not found for jd_id='{jd_id}'."
            )

        # ---------------------------------------------------------
        # 2. Validate stored JD
        # ---------------------------------------------------------

        try:
            # MongoDB documents include `_id` (set by the repository).
            # JobDescription forbids extra fields, so strip `_id`
            # before schema validation.
            validation_document = dict(jd_document)
            validation_document.pop("_id", None)

            job_description = JobDescription.model_validate(
                validation_document
            )
        except Exception as exc:
            raise ValueError(
                f"Invalid stored job description "
                f"for jd_id='{jd_id}': {exc}"
            ) from exc

        # ---------------------------------------------------------
        # 3. Check structured data
        # ---------------------------------------------------------

        if job_description.structured_data is None:
            raise ValueError(
                f"Job description '{jd_id}' "
                f"does not contain structured data."
            )

        jd_object = job_description.structured_data

        # ---------------------------------------------------------
        # 4. Build JD evidence
        # ---------------------------------------------------------

        evidence = evidence_service.build_jd_evidence(
            jd_object
        )

        if not evidence:
            raise ValueError(
                f"Job description '{jd_id}' "
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
                f"for JD '{jd_id}'."
            )

        # ---------------------------------------------------------
        # 6. Save embeddings to MongoDB
        # ---------------------------------------------------------

        await jd_embedding_repository.save(
            jd_id=jd_id,
            embeddings=embedded_evidence,
        )

        # ---------------------------------------------------------
        # 7. Return generation information
        # ---------------------------------------------------------

        return {
            "jd_id": jd_id,
            "evidence_count": len(evidence),
            "embedding_count": len(embedded_evidence),
            "embedding_dimension": len(
                embedded_evidence[0]["embedding"]
            ),
            "status": "completed",
        }


job_description_embedding_generation_service = (
    JobDescriptionEmbeddingGenerationService()
)
