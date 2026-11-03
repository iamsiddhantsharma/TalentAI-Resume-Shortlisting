from app.database.mongodb import mongodb
from app.database.collections import MongoCollections
from app.database.jd_embedding_repository import (
    jd_embedding_repository,
)
from app.schemas.job_description import JobDescription


class JobDescriptionRepository:
    """
    MongoDB repository for Job Description results.

    Stores the complete structured JD so that the
    future matching engine can use it.
    """

    COLLECTION_NAME = MongoCollections.JOB_DESCRIPTIONS

    def _collection(self):
        """
        Return the MongoDB Job Description collection.
        """

        database = mongodb.get_database()

        return database[self.COLLECTION_NAME]

    async def save(
        self,
        job_description: JobDescription,
    ) -> None:
        """
        Store the active Job Description.

        TalentAI supports exactly one JD at a time.
        Any previously stored JD documents are removed
        before the new JD is saved.
        """

        collection = self._collection()

        # Enforce single-JD rule at the persistence boundary.
        # Resumes and resume embeddings are intentionally
        # left untouched.
        await collection.delete_many({})

        # Previous active JD embeddings belong to the old JD
        # and must no longer remain active.
        await jd_embedding_repository.delete()

        document = job_description.model_dump(
            mode="json"
        )

        document["_id"] = (
            job_description.jd_id
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
        jd_id: str,
    ) -> dict | None:
        """
        Get one Job Description by jd_id.
        """

        collection = self._collection()

        return await collection.find_one(
            {
                "_id": jd_id
            }
        )

    async def get_active(
        self,
    ) -> dict | None:
        """
        Get the currently active Job Description.

        Under the TalentAI single-active-JD rule, at most
        one Job Description is stored at any given time.
        """

        collection = self._collection()

        return await collection.find_one({})

    async def get_all(
        self,
    ) -> list[dict]:

        """
        Get all stored Job Descriptions.
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
        Return total number of stored Job Descriptions.
        """

        collection = self._collection()

        return await collection.count_documents({})

    async def delete(
        self,
        jd_id: str,
    ) -> None:
        """
        Delete one Job Description.
        """

        collection = self._collection()

        await collection.delete_one(
            {
                "_id": jd_id
            }
        )

    async def delete_all(
        self,
    ) -> None:
        """
        Delete all Job Descriptions.

        Development/testing use only.
        """

        collection = self._collection()

        await collection.delete_many({})


jd_repository = JobDescriptionRepository()
