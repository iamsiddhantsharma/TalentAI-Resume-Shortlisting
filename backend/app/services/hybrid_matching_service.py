from app.database.jd_repository import jd_repository
from app.database.resume_repository import resume_repository
from app.database.jd_embedding_repository import jd_embedding_repository
from app.database.resume_embedding_repository import resume_embedding_repository

from app.schemas.job_description import JobDescription
from app.schemas.job_description_object import JobDescriptionObject
from app.schemas.processing_result import ProcessingResult

from app.services.llm_skill_matching_service import (
    llm_skill_matching_service,
)
from app.services.semantic_retrieval_service import semantic_retrieval_service
from app.services.experience_llm_service import experience_llm_service
from app.services.experience_matching_service import experience_matching_service


class HybridMatchingService:
    """
    Orchestrates all matching signals for one resume against one JD.

    Responsibilities:
    - Load structured JD and resume data.
    - Load already-generated embeddings.
    - Run LLM required skill matching.
    - Run semantic evidence retrieval.
    - Run Qwen only for professional experience relevance.
    - Run deterministic experience matching.
    - Return raw matching signals.

    This service does NOT:
    - calculate a final match score
    - apply weights
    - rank candidates
    - make hiring decisions
    - generate embeddings
    """

    def __init__(self):
        self.top_k = 5
        self.min_similarity_threshold = 0.65

    async def match_resume(
        self,
        jd_id: str,
        upload_id: str,
        filename: str,
        preloaded_jd: JobDescription | JobDescriptionObject | dict | None = None,
        preloaded_jd_embeddings: list[dict] | None = None,
    ) -> dict:
        """
        Match one resume against one job description.

        Supports optional preloaded JD and JD embeddings to eliminate redundant
        database queries during batch processing while remaining fully backward
        compatible with existing callers.
        """

        # =========================================================
        # 1. LOAD STRUCTURED JOB DESCRIPTION
        # =========================================================

        if preloaded_jd is not None:
            if isinstance(preloaded_jd, JobDescriptionObject):
                jd_object = preloaded_jd
            elif isinstance(preloaded_jd, JobDescription):
                if preloaded_jd.jd_id and preloaded_jd.jd_id != jd_id:
                    raise ValueError(
                        f"Preloaded JD ID '{preloaded_jd.jd_id}' does not match requested jd_id '{jd_id}'."
                    )
                if preloaded_jd.structured_data is None:
                    raise ValueError(
                        f"Job description '{jd_id}' does not contain structured data."
                    )
                jd_object = preloaded_jd.structured_data
            elif isinstance(preloaded_jd, dict):
                validation_document = dict(preloaded_jd)
                validation_document.pop("_id", None)
                job_desc = JobDescription.model_validate(validation_document)
                if job_desc.structured_data is None:
                    raise ValueError(
                        f"Job description '{jd_id}' does not contain structured data."
                    )
                jd_object = job_desc.structured_data
            else:
                raise ValueError("Invalid preloaded_jd type provided.")
        else:
            jd_document = await jd_repository.get(jd_id)

            if jd_document is None:
                raise ValueError(
                    f"Job description not found for jd_id='{jd_id}'."
                )

            try:
                # MongoDB documents include `_id` (set by the repository).
                # JobDescription forbids extra fields, so strip `_id`
                # before schema validation. Do not mutate the original.
                validation_document = dict(jd_document)
                validation_document.pop("_id", None)

                job_description = JobDescription.model_validate(
                    validation_document
                )
            except Exception as exc:
                raise ValueError(
                    f"Invalid stored job description for "
                    f"jd_id='{jd_id}': {exc}"
                ) from exc

            if job_description.structured_data is None:
                raise ValueError(
                    f"Job description '{jd_id}' "
                    f"does not contain structured data."
                )

            jd_object = job_description.structured_data

        # =========================================================
        # 2. LOAD ACTIVE JD EMBEDDINGS
        # =========================================================

        if preloaded_jd_embeddings is not None:
            jd_embeddings = preloaded_jd_embeddings
            if not jd_embeddings:
                raise ValueError(
                    f"JD '{jd_id}' has no stored evidence embeddings."
                )
        else:
            jd_embedding_document = (
                await jd_embedding_repository.get_by_jd_id(jd_id)
            )

            if jd_embedding_document is None:
                raise ValueError(
                    f"Embeddings not found for active JD '{jd_id}'."
                )

            jd_embeddings = jd_embedding_document.get(
                "embeddings",
                [],
            )

            if not jd_embeddings:
                raise ValueError(
                    f"JD '{jd_id}' has no stored evidence embeddings."
                )


        # =========================================================
        # 3. LOAD STRUCTURED RESUME
        # =========================================================

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

        try:
            processing_result = ProcessingResult.model_validate(
                resume_document
            )
        except Exception as exc:
            raise ValueError(
                f"Invalid stored resume for "
                f"upload_id='{upload_id}', "
                f"filename='{filename}': {exc}"
            ) from exc

        # IMPORTANT:
        # ProcessingResult uses `resume_data`,
        # not `structured_data`.

        if processing_result.resume_data is None:
            raise ValueError(
                f"Resume '{filename}' "
                f"does not contain structured resume data."
            )

        resume_object = processing_result.resume_data

        # =========================================================
        # 4. LOAD STORED RESUME EMBEDDINGS
        # =========================================================

        resume_embedding_document = (
            await resume_embedding_repository.get(
                upload_id=upload_id,
                filename=filename,
            )
        )

        if resume_embedding_document is None:
            raise ValueError(
                f"Embeddings not found for resume "
                f"upload_id='{upload_id}', "
                f"filename='{filename}'."
            )

        resume_embeddings = resume_embedding_document.get(
            "embeddings",
            [],
        )

        if not resume_embeddings:
            raise ValueError(
                f"Resume '{filename}' "
                f"has no stored evidence embeddings."
            )

        # =========================================================
        # 5. LLM SKILL MATCHING
        # =========================================================

        exact_skill_result = (
            await llm_skill_matching_service.match_required_skills(
                job_description=jd_object,
                resume=resume_object,
            )
        )

        # =========================================================
        # 6. SEMANTIC EVIDENCE RETRIEVAL
        # =========================================================

        # Select only JD responsibilities (retrieves against projects + experience)
        responsibility_jd_embeddings = [
            evidence
            for evidence in jd_embeddings
            if evidence.get("section") == "responsibilities"
        ]

        # Select only JD tools and technologies (retrieves against projects only)
        tools_jd_embeddings = [
            evidence
            for evidence in jd_embeddings
            if evidence.get("section") == "tools_and_technologies"
        ]

        responsibilities_retrieval_results = (
            semantic_retrieval_service
            .retrieve_for_all_jd_evidence(
                jd_embeddings=responsibility_jd_embeddings,
                resume_embeddings=resume_embeddings,
                top_k=self.top_k,
                min_similarity_threshold=self.min_similarity_threshold,
            )
        )

        tools_retrieval_results = (
            semantic_retrieval_service
            .retrieve_for_all_jd_evidence(
                jd_embeddings=tools_jd_embeddings,
                resume_embeddings=resume_embeddings,
                top_k=self.top_k,
                min_similarity_threshold=self.min_similarity_threshold,
            )
        )

        # =========================================================
        # 7. EXPERIENCE RELEVANCE
        # =========================================================

        relevance_results = []

        if (
            experience_matching_service
            .has_meaningful_experience_requirement(
                jd_object
            )
        ):
            # Qwen is used ONLY to determine whether
            # professional experiences are relevant.

            experience_relevance = (
                await experience_llm_service.evaluate_experiences(
                    resume=resume_object,
                    job_description=jd_object,
                )
            )

            relevance_results = [
                decision.model_dump(mode="json")
                for decision
                in experience_relevance.experience_decisions
            ]

        # =========================================================
        # 8. DETERMINISTIC EXPERIENCE MATCHING
        # =========================================================

        experience_result = (
            experience_matching_service.match_experience(
                resume=resume_object,
                job_description=jd_object,
                relevance_results=relevance_results,
            )
        )

        # =========================================================
        # 9. RETURN RAW MATCHING SIGNALS
        # =========================================================

        return {
            "jd_id": jd_id,
            "upload_id": upload_id,
            "filename": filename,

            "exact_matching": exact_skill_result,

            "semantic_retrieval": {
                "top_k": self.top_k,
                "responsibilities_retrieval": {
                    "top_k": self.top_k,
                    "results": responsibilities_retrieval_results,
                },
                "tools_and_technologies_retrieval": {
                    "top_k": self.top_k,
                    "results": tools_retrieval_results,
                },
                "results": (
                    responsibilities_retrieval_results
                    + tools_retrieval_results
                ),
            },

            "experience_matching": experience_result,
        }


hybrid_matching_service = HybridMatchingService()
