from app.database.mongodb import mongodb


class JobDescriptionEmbeddingRepository:
    """
    Stores and retrieves the embeddings for the currently
    active Job Description.

    For the current TalentAI workflow, only one JD is active
    at a time.

    One MongoDB document represents the complete embedding
    data for that JD.

    Example:

    active JD
        └── embeddings
             ├── required skill embedding
             ├── responsibility embedding
             ├── experience requirement embedding
             ├── technology embedding
             └── ...

    The repository does not generate embeddings.
    It only persists them in MongoDB.
    """

    COLLECTION_NAME = "jd_embeddings"

    ACTIVE_DOCUMENT_ID = "active_jd"

    def _collection(self):
        database = mongodb.get_database()
        return database[self.COLLECTION_NAME]

    async def save(
        self,
        jd_id: str,
        embeddings: list[dict],
    ) -> None:
        """
        Save all embeddings belonging to the active JD.

        Only one JD embedding document is maintained.

        If a new JD is processed, the previous active JD
        embedding document is replaced.
        """

        collection = self._collection()

        document = {
            "_id": self.ACTIVE_DOCUMENT_ID,
            "jd_id": jd_id,
            "embeddings": embeddings,
        }

        await collection.replace_one(
            {"_id": self.ACTIVE_DOCUMENT_ID},
            document,
            upsert=True,
        )

    async def get(self) -> dict | None:
        """
        Retrieve the complete embedding document
        for the active JD.
        """

        collection = self._collection()

        return await collection.find_one(
            {"_id": self.ACTIVE_DOCUMENT_ID}
        )

    async def get_by_jd_id(
        self,
        jd_id: str,
    ) -> dict | None:
        """
        Retrieve the active JD embedding document only
        if it belongs to the requested JD.
        """

        collection = self._collection()

        return await collection.find_one(
            {
                "_id": self.ACTIVE_DOCUMENT_ID,
                "jd_id": jd_id,
            }
        )

    async def count(self) -> int:
        """
        Count JD embedding documents.

        For the current architecture this should normally
        be 0 or 1.
        """

        collection = self._collection()

        return await collection.count_documents({})

    async def delete(self) -> None:
        """
        Delete the active JD embedding document.
        """

        collection = self._collection()

        await collection.delete_one(
            {"_id": self.ACTIVE_DOCUMENT_ID}
        )


jd_embedding_repository = JobDescriptionEmbeddingRepository()
