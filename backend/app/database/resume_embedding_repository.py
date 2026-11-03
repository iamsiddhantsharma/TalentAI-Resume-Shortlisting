from app.database.mongodb import mongodb


class ResumeEmbeddingRepository:
    """
    Stores and retrieves all semantic embeddings belonging
    to a single resume.

    One MongoDB document represents one resume.

    Example:

    resume_001
        └── embeddings
             ├── skill embedding
             ├── project embedding
             ├── experience embedding
             └── ...

    The repository does not generate embeddings.
    It only persists them in MongoDB.
    """

    COLLECTION_NAME = "resume_embeddings"

    def _collection(self):
        database = mongodb.get_database()
        return database[self.COLLECTION_NAME]

    async def save(
        self,
        upload_id: str,
        filename: str,
        embeddings: list[dict],
    ) -> None:
        """
        Save all embeddings belonging to one resume.

        If the same resume is processed again, its previous
        embedding document is replaced.
        """

        collection = self._collection()

        document = {
            "_id": f"{upload_id}:{filename}",
            "upload_id": upload_id,
            "filename": filename,
            "embeddings": embeddings,
        }

        await collection.replace_one(
            {"_id": document["_id"]},
            document,
            upsert=True,
        )

    async def get(
        self,
        upload_id: str,
        filename: str,
    ) -> dict | None:
        """
        Retrieve the complete embedding document for one resume.
        """

        collection = self._collection()

        document_id = f"{upload_id}:{filename}"

        return await collection.find_one(
            {"_id": document_id}
        )

    async def get_by_upload(
        self,
        upload_id: str,
    ) -> list[dict]:
        """
        Retrieve all embedding documents belonging to an upload.
        """

        collection = self._collection()

        cursor = collection.find(
            {"upload_id": upload_id}
        )

        return await cursor.to_list(length=None)

    async def get_all(self) -> list[dict]:
        """
        Retrieve all resume embedding documents.
        """

        collection = self._collection()

        cursor = collection.find({})

        return await cursor.to_list(length=None)

    async def count(self) -> int:
        """
        Count the number of resume embedding documents.
        """

        collection = self._collection()

        return await collection.count_documents({})

    async def delete_by_upload(
        self,
        upload_id: str,
    ) -> None:
        """
        Delete all embedding documents belonging to an upload.
        """

        collection = self._collection()

        await collection.delete_many(
            {"upload_id": upload_id}
        )

    async def delete(
        self,
        upload_id: str,
        filename: str,
    ) -> None:
        """
        Delete embedding document for a single resume.
        """

        collection = self._collection()

        document_id = f"{upload_id}:{filename}"

        await collection.delete_one(
            {"_id": document_id}
        )

    async def delete_all(self) -> None:
        """
        Delete all resume embedding documents.
        """

        collection = self._collection()

        await collection.delete_many({})



resume_embedding_repository = ResumeEmbeddingRepository()
