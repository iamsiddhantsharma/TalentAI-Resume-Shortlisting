from math import sqrt


class SemanticRetrievalService:
    """
    Performs semantic retrieval between Job Description (JD)
    evidence and Resume evidence.

    The service supports section-aware retrieval.

    This means different JD sections are matched against
    appropriate Resume sections instead of blindly comparing
    every JD item against every Resume item.

    The service does NOT:
    - calculate final candidate scores
    - apply ranking weights
    - perform exact keyword matching
    - calculate total experience
    - call the LLM
    - make hiring decisions

    Its responsibility is semantic evidence retrieval.
    """

    # ---------------------------------------------------------
    # SECTION MATCHING POLICY
    # ---------------------------------------------------------

    SECTION_MAPPING = {
        "responsibilities": {
            "projects",
            "experience",
        },

        "tools_and_technologies": {
            "projects",
        },
    }

    DEFAULT_MIN_SIMILARITY_THRESHOLD = 0.65

    def __init__(
        self,
        min_similarity_threshold: float = DEFAULT_MIN_SIMILARITY_THRESHOLD,
    ):
        self.min_similarity_threshold = min_similarity_threshold

    # ---------------------------------------------------------
    # COSINE SIMILARITY
    # ---------------------------------------------------------

    def cosine_similarity(
        self,
        vector_a: list[float],
        vector_b: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Our BGE embeddings are normalized, but we explicitly
        calculate cosine similarity here to keep the retrieval
        logic clear and independently testable.
        """

        if not vector_a or not vector_b:
            raise ValueError(
                "Vectors cannot be empty."
            )

        if len(vector_a) != len(vector_b):
            raise ValueError(
                "Vectors must have the same dimensions."
            )

        dot_product = sum(
            a * b
            for a, b in zip(vector_a, vector_b)
        )

        magnitude_a = sqrt(
            sum(a * a for a in vector_a)
        )

        magnitude_b = sqrt(
            sum(b * b for b in vector_b)
        )

        if magnitude_a == 0 or magnitude_b == 0:
            raise ValueError(
                "Cannot calculate similarity for a zero vector."
            )

        return dot_product / (
            magnitude_a * magnitude_b
        )

    # ---------------------------------------------------------
    # GET ALLOWED RESUME SECTIONS
    # ---------------------------------------------------------

    def get_allowed_resume_sections(
        self,
        jd_section: str,
    ) -> set[str]:
        """
        Return the Resume sections that are allowed to
        participate in semantic retrieval for a particular
        JD section.

        Example:

        responsibilities
            →
        {
            "projects",
            "experience"
        }

        tools_and_technologies
            →
        {
            "projects"
        }
        """

        return self.SECTION_MAPPING.get(
            jd_section,
            set(),
        )

    # ---------------------------------------------------------
    # SECTION-AWARE RETRIEVAL
    # ---------------------------------------------------------

    def retrieve_for_jd_evidence(
        self,
        jd_evidence: dict,
        resume_embeddings: list[dict],
        top_k: int = 5,
        min_similarity_threshold: float | None = None,
    ) -> list[dict]:
        """
        Retrieve the most semantically similar Resume
        evidence for one JD evidence unit.

        Only candidate evidence with similarity >= min_similarity_threshold
        (default 0.65) is retained.

        The JD evidence must contain:

        - section
        - item_index
        - text
        - embedding

        Resume evidence must contain:

        - section
        - item_index
        - text
        - embedding

        Only Resume sections allowed by SECTION_MAPPING
        are considered.
        """

        if not jd_evidence:
            raise ValueError(
                "JD evidence cannot be empty."
            )

        jd_embedding = jd_evidence.get(
            "embedding"
        )

        if not jd_embedding:
            raise ValueError(
                "JD evidence must contain an embedding."
            )

        jd_section = jd_evidence.get(
            "section"
        )

        if not jd_section:
            raise ValueError(
                "JD evidence must contain a section."
            )

        if not resume_embeddings:
            return []

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        threshold = (
            min_similarity_threshold
            if min_similarity_threshold is not None
            else self.min_similarity_threshold
        )

        allowed_sections = (
            self.get_allowed_resume_sections(
                jd_section
            )
        )

        if not allowed_sections:
            return []

        results = []

        for resume_evidence in resume_embeddings:

            resume_section = resume_evidence.get(
                "section"
            )

            if not resume_section or resume_section not in allowed_sections:
                continue

            resume_embedding = (
                resume_evidence.get("embedding")
            )

            if not resume_embedding:
                continue

            similarity = self.cosine_similarity(
                jd_embedding,
                resume_embedding,
            )

            similarity_float = float(
                similarity
            )

            if similarity_float < threshold:
                continue

            results.append({
                "jd_section": jd_section,
                "jd_item_index": jd_evidence.get(
                    "item_index"
                ),
                "jd_text": jd_evidence.get(
                    "text"
                ),

                "resume_section": resume_section,
                "resume_item_index": (
                    resume_evidence.get(
                        "item_index"
                    )
                ),
                "resume_text": (
                    resume_evidence.get(
                        "text"
                    )
                ),

                "similarity": similarity_float,
            })

        results.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        return results[:top_k]

    # ---------------------------------------------------------
    # RETRIEVE FOR ALL JD EVIDENCE
    # ---------------------------------------------------------

    def retrieve_for_all_jd_evidence(
        self,
        jd_embeddings: list[dict],
        resume_embeddings: list[dict],
        top_k: int = 5,
        min_similarity_threshold: float | None = None,
    ) -> list[dict]:
        """
        Retrieve semantic matches for every JD evidence unit.

        Each JD evidence item is processed independently.

        Returns a list where every element represents one
        JD requirement and its strongest Resume evidence.
        """

        if not jd_embeddings:
            return []

        if not resume_embeddings:
            return []

        threshold = (
            min_similarity_threshold
            if min_similarity_threshold is not None
            else self.min_similarity_threshold
        )

        results = []

        for jd_evidence in jd_embeddings:

            matches = self.retrieve_for_jd_evidence(
                jd_evidence=jd_evidence,
                resume_embeddings=resume_embeddings,
                top_k=top_k,
                min_similarity_threshold=threshold,
            )

            results.append({
                "jd_section": jd_evidence.get(
                    "section"
                ),
                "jd_item_index": jd_evidence.get(
                    "item_index"
                ),
                "jd_text": jd_evidence.get(
                    "text"
                ),
                "matches": matches,
            })

        return results


semantic_retrieval_service = SemanticRetrievalService()

