from app.database.mongodb import mongodb
from app.database.collections import MongoCollections
from app.schemas.processing_result import ProcessingResult


class ResumeRepository:
    """
    MongoDB repository for storing processed resume results.

    This repository is responsible only for database persistence.

    Matching, ranking, embeddings, and candidate scoring
    do NOT belong here.
    """

    COLLECTION_NAME = MongoCollections.RESUMES

    def _collection(self):
        """
        Return the MongoDB resumes collection.
        """

        database = mongodb.get_database()

        return database[self.COLLECTION_NAME]

    async def save(
        self,
        result: ProcessingResult,
    ) -> None:
        """
        Store or update one processed resume.
        """

        collection = self._collection()

        document = result.model_dump(
            mode="json"
        )

        document["_id"] = (
            f"{result.upload_id}:{result.filename}"
        )

        await collection.replace_one(
            {
                "_id": document["_id"]
            },
            document,
            upsert=True,
        )

    async def get(
        self,
        upload_id: str,
        filename: str,
    ) -> dict | None:
        """
        Get one resume from MongoDB.
        """

        collection = self._collection()

        document_id = (
            f"{upload_id}:{filename}"
        )

        return await collection.find_one(
            {
                "_id": document_id
            }
        )

    async def get_by_upload(
        self,
        upload_id: str,
    ) -> list[dict]:
        """
        Get all resumes belonging to one upload.
        """

        collection = self._collection()

        cursor = collection.find(
            {
                "upload_id": upload_id
            }
        )

        return await cursor.to_list(
            length=None
        )

    async def get_all(
        self,
    ) -> list[dict]:
        """
        Get all stored resumes.
        """

        collection = self._collection()

        cursor = collection.find({})

        return await cursor.to_list(
            length=None
        )

    async def count(
        self,
    ) -> int:
        """
        Return total number of stored resumes.
        """

        collection = self._collection()

        return await collection.count_documents({})

    async def delete_by_upload(
        self,
        upload_id: str,
    ) -> None:
        """
        Delete all resumes belonging to one upload.

        This supports the privacy-first workflow:

        HR uploads resumes
            ↓
        Processing
            ↓
        Results
            ↓
        HR downloads results
            ↓
        Candidate data can be deleted
        """

        collection = self._collection()

        await collection.delete_many(
            {
                "upload_id": upload_id
            }
        )

    async def delete_all(
        self,
    ) -> None:
        """
        Delete all resume documents.

        Development/testing use only.
        """

        collection = self._collection()

        await collection.delete_many({})


resume_repository = ResumeRepository()
