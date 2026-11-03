from datetime import datetime, timezone
import logging
from typing import Any
from pymongo import ASCENDING, DESCENDING

from app.database.collections import MongoCollections
from app.database.mongodb import mongodb

logger = logging.getLogger(__name__)


class RankingJobRepository:
    """
    MongoDB repository for managing asynchronous ranking jobs and progress tracking.
    """

    COLLECTION_NAME = MongoCollections.RANKING_JOBS

    def _collection(self):
        try:
            database = mongodb.get_database()
            if isinstance(database, dict):
                return database.get(self.COLLECTION_NAME)
            return database[self.COLLECTION_NAME]
        except RuntimeError:
            return None

    async def create_indexes(self) -> None:
        """
        Create necessary indexes for job lookup, status filtering, and cleanup.
        """
        try:
            col = self._collection()
            if col is None or isinstance(col, dict):
                return
            await col.create_index([("job_id", ASCENDING)], unique=True)
            await col.create_index([("status", ASCENDING)])
            await col.create_index([("batch_id", ASCENDING)])
            await col.create_index([("created_at", DESCENDING)])
        except Exception as exc:
            logger.warning("Could not create indexes on ranking_jobs: %s", exc)

    async def create_job(self, job_doc: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a new ranking job document.
        """
        col = self._collection()
        if col is None:
            raise RuntimeError("Database not connected.")
        doc = dict(job_doc)
        if "_id" not in doc:
            doc["_id"] = doc.get("job_id")
        await col.insert_one(doc)
        return doc

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """
        Retrieve a ranking job by job_id.
        """
        col = self._collection()
        if col is None:
            return None
        doc = await col.find_one({"job_id": job_id})
        if doc and "_id" in doc:
            doc.pop("_id", None)
        return doc

    async def update_job(self, job_id: str, updates: dict[str, Any]) -> None:
        """
        Update specific fields of an existing ranking job document.
        """
        col = self._collection()
        if col is None:
            return
        await col.update_one(
            {"job_id": job_id},
            {"$set": updates},
        )

    async def reconcile_stale_jobs(self) -> int:
        """
        Mark any in-flight 'queued' or 'processing' jobs as 'interrupted'.
        Called during application startup to reconcile orphaned background tasks
        caused by unexpected process restarts.
        """
        col = self._collection()
        if col is None or isinstance(col, dict):
            return 0
        now = datetime.now(timezone.utc).isoformat()
        res = await col.update_many(
            {"status": {"$in": ["queued", "processing"]}},
            {
                "$set": {
                    "status": "interrupted",
                    "finished_at": now,
                    "error": "Job was interrupted by server restart.",
                }
            },
        )
        count = res.modified_count if hasattr(res, "modified_count") else 0
        if count > 0:
            logger.warning("Reconciled %d stale in-flight ranking jobs to 'interrupted'.", count)
        return count


ranking_job_repository = RankingJobRepository()
