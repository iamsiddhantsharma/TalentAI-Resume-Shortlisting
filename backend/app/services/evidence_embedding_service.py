from app.services.embedding_service import embedding_service


class EvidenceEmbeddingService:
    """
    Generates embeddings for resume and JD evidence units.

    EvidenceService creates the evidence and its metadata.
    EmbeddingService converts the evidence text into vectors.
    This service combines the metadata and embedding.
    """

    def embed_evidence(
        self,
        evidence: list[dict],
    ) -> list[dict]:
        """
        Generate an embedding for every evidence unit.

        Each returned item contains:
        - source_type
        - section
        - item_index
        - text
        - embedding
        """

        if not evidence:
            return []

        valid_evidence = [
            item
            for item in evidence
            if item.get("text")
        ]

        if not valid_evidence:
            return []

        texts = [
            item["text"]
            for item in valid_evidence
        ]

        embeddings = embedding_service.generate_embeddings(
            texts
        )

        embedded_evidence = []

        for item, embedding in zip(
            valid_evidence,
            embeddings,
        ):
            embedded_evidence.append(
                {
                    "source_type": item["source_type"],
                    "section": item["section"],
                    "item_index": item["item_index"],
                    "text": item["text"],
                    "embedding": embedding,
                }
            )

        return embedded_evidence


evidence_embedding_service = EvidenceEmbeddingService()
