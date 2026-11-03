from app.schemas.resume_object import ResumeObject
from app.schemas.job_description_object import JobDescriptionObject
from app.services.embedding_service import embedding_service


class ExperienceRelevanceService:
    """
    Generates semantic features for determining whether a resume
    experience is relevant to one of the preferred experience
    domains specified in a Job Description.

    IMPORTANT:
    This service does NOT make a final RELEVANT / IRRELEVANT decision.

    It produces the features required by the later relevance
    decision layer.

    Current architecture:

        Resume Experience
                ↓
        Information Sufficiency
                ↓
        Experience Embedding
                ↓
        Compare with every preferred domain
                ↓
        Domain Similarities
                ↓
        Top-1 / Top-2 / Margin
                ↓
        Later Calibration / Decision Layer
    """

    # Minimum amount of meaningful information required before
    # semantic relevance can be evaluated.
    MIN_MEANINGFUL_WORDS = 4

    def get_preferred_domains(
        self,
        job_description: JobDescriptionObject,
    ) -> list[str]:
        """
        Extract unique preferred domains from all experience
        requirements in the Job Description.
        """

        preferred_domains = []

        for requirement in job_description.experience_requirements:

            for domain in requirement.preferred_domains:

                if not domain:
                    continue

                cleaned_domain = domain.strip()

                if not cleaned_domain:
                    continue

                # Case-insensitive duplicate prevention
                if not any(
                    existing.lower() == cleaned_domain.lower()
                    for existing in preferred_domains
                ):
                    preferred_domains.append(cleaned_domain)

        return preferred_domains

    def build_experience_text(self, experience) -> str:
        """
        Convert one Resume Experience object into semantic text.
        """

        parts = []

        if experience.role:
            role = experience.role.strip()

            if role:
                parts.append(f"Role: {role}")

        if experience.company:
            company = experience.company.strip()

            if company:
                parts.append(f"Company: {company}")

        if experience.description:
            description = experience.description.strip()

            if description:
                parts.append(f"Work: {description}")

        return " | ".join(parts)

    def count_meaningful_words(self, text: str) -> int:
        """
        Count meaningful whitespace-separated words.

        This is intentionally simple at the current stage.
        We will calibrate the sufficiency logic later using
        real examples.
        """

        if not text:
            return 0

        words = [
            word.strip()
            for word in text.split()
            if word.strip()
        ]

        return len(words)

    def check_information_sufficiency(
        self,
        experience_text: str,
    ) -> dict:
        """
        Determine whether the experience contains enough
        information for semantic relevance analysis.

        This is NOT a relevance decision.

        It only answers:

            "Do we have enough information to make
             a meaningful semantic comparison?"
        """

        meaningful_word_count = self.count_meaningful_words(
            experience_text
        )

        has_description = "Work:" in experience_text

        sufficient = (
            meaningful_word_count >= self.MIN_MEANINGFUL_WORDS
            and has_description
        )

        return {
            "sufficient": sufficient,
            "meaningful_word_count": meaningful_word_count,
            "has_description": has_description,
        }

    def calculate_similarity(
        self,
        vector_a: list[float],
        vector_b: list[float],
    ) -> float:
        """
        Calculate cosine similarity.

        Because BGE embeddings are generated with
        normalize_embeddings=True, cosine similarity
        is equivalent to the dot product.
        """

        if not vector_a or not vector_b:
            raise ValueError(
                "Both vectors must be non-empty."
            )

        if len(vector_a) != len(vector_b):
            raise ValueError(
                "Vectors must have the same dimensions."
            )

        similarity = sum(
            a * b
            for a, b in zip(vector_a, vector_b)
        )

        return float(similarity)

    def generate_domain_embeddings(
        self,
        preferred_domains: list[str],
    ) -> dict[str, list[float]]:
        """
        Generate one independent embedding for every
        preferred experience domain.
        """

        domain_embeddings = {}

        for domain in preferred_domains:
            domain_embeddings[domain] = (
                embedding_service.generate_embedding(domain)
            )

        return domain_embeddings

    def calculate_domain_matches(
        self,
        experience_embedding: list[float],
        domain_embeddings: dict[str, list[float]],
    ) -> list[dict]:
        """
        Compare one resume experience against every
        preferred domain.
        """

        domain_matches = []

        for domain, domain_embedding in domain_embeddings.items():

            similarity = self.calculate_similarity(
                experience_embedding,
                domain_embedding,
            )

            domain_matches.append(
                {
                    "domain": domain,
                    "similarity": round(
                        similarity,
                        4,
                    ),
                }
            )

        # Highest similarity first
        domain_matches.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        return domain_matches

    def calculate_ranking_features(
        self,
        domain_matches: list[dict],
    ) -> dict:
        """
        Calculate top-1, top-2 and margin features.

        These are FEATURES, not final relevance decisions.
        """

        if not domain_matches:
            return {
                "top1_domain": None,
                "top1_score": None,
                "top2_domain": None,
                "top2_score": None,
                "margin": None,
                "number_of_domains": 0,
            }

        top1 = domain_matches[0]

        top1_domain = top1["domain"]
        top1_score = top1["similarity"]

        # If there is only one preferred domain,
        # top-2 and margin do not exist.
        if len(domain_matches) == 1:

            return {
                "top1_domain": top1_domain,
                "top1_score": top1_score,
                "top2_domain": None,
                "top2_score": None,
                "margin": None,
                "number_of_domains": 1,
            }

        top2 = domain_matches[1]

        top2_domain = top2["domain"]
        top2_score = top2["similarity"]

        margin = round(
            top1_score - top2_score,
            4,
        )

        return {
            "top1_domain": top1_domain,
            "top1_score": top1_score,
            "top2_domain": top2_domain,
            "top2_score": top2_score,
            "margin": margin,
            "number_of_domains": len(domain_matches),
        }

    def match_experience_relevance(
        self,
        resume: ResumeObject,
        job_description: JobDescriptionObject,
    ) -> list[dict]:
        """
        Generate relevance features for every resume experience.

        IMPORTANT:
        This method intentionally does NOT classify an experience
        as RELEVANT or IRRELEVANT.

        It generates the evidence/features that a later
        calibration and decision layer will use.
        """

        preferred_domains = self.get_preferred_domains(
            job_description
        )

        # No preferred domains means that this experience
        # relevance component is not applicable.
        if not preferred_domains:

            return [
                {
                    "experience_index": index,
                    "experience_text": self.build_experience_text(
                        experience
                    ),
                    "information_sufficiency": {
                        "sufficient": False,
                        "meaningful_word_count": 0,
                        "has_description": False,
                    },
                    "preferred_domains": [],
                    "domain_matches": [],
                    "top1_domain": None,
                    "top1_score": None,
                    "top2_domain": None,
                    "top2_score": None,
                    "margin": None,
                    "number_of_domains": 0,
                    "status": "NOT_APPLICABLE",
                }
                for index, experience in enumerate(
                    resume.experience
                )
            ]

        # Generate each domain embedding only once.
        domain_embeddings = (
            self.generate_domain_embeddings(
                preferred_domains
            )
        )

        results = []

        for index, experience in enumerate(
            resume.experience
        ):

            experience_text = self.build_experience_text(
                experience
            )

            information = (
                self.check_information_sufficiency(
                    experience_text
                )
            )

            # If there is not enough information,
            # do not make a semantic relevance decision.
            if not information["sufficient"]:

                results.append(
                    {
                        "experience_index": index,
                        "experience_text": experience_text,
                        "information_sufficiency": information,
                        "preferred_domains": preferred_domains,
                        "domain_matches": [],
                        "top1_domain": None,
                        "top1_score": None,
                        "top2_domain": None,
                        "top2_score": None,
                        "margin": None,
                        "number_of_domains": len(
                            preferred_domains
                        ),
                        "status": "INSUFFICIENT_INFORMATION",
                    }
                )

                continue

            # Generate experience embedding.
            experience_embedding = (
                embedding_service.generate_embedding(
                    experience_text
                )
            )

            # Compare against EVERY preferred domain.
            domain_matches = (
                self.calculate_domain_matches(
                    experience_embedding,
                    domain_embeddings,
                )
            )

            # Calculate ranking features.
            ranking_features = (
                self.calculate_ranking_features(
                    domain_matches
                )
            )

            results.append(
                {
                    "experience_index": index,
                    "experience_text": experience_text,
                    "information_sufficiency": information,
                    "preferred_domains": preferred_domains,
                    "domain_matches": domain_matches,
                    **ranking_features,
                    # Temporary status:
                    # This is NOT a relevance decision.
                    # It tells the next stage that features
                    # are ready for classification.
                    "status": "FEATURES_READY",
                }
            )

        return results


experience_relevance_service = ExperienceRelevanceService()
