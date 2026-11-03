from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Generates semantic embeddings for TalentAI.

    The embedding model is responsible for converting
    text into numerical vectors that can later be
    stored and searched using MongoDB Vector Search.
    """

    MODEL_NAME = "BAAI/bge-large-en-v1.5"

    def __init__(self):
        self.model = SentenceTransformer(self.MODEL_NAME)

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate one embedding vector for a single text.
        """

        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    def generate_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        """

        if not texts:
            return []

        cleaned_texts = [
            text.strip()
            for text in texts
            if text and text.strip()
        ]

        if not cleaned_texts:
            return []

        embeddings = self.model.encode(
            cleaned_texts,
            normalize_embeddings=True,
        )

        return embeddings.tolist()


embedding_service = EmbeddingService()
