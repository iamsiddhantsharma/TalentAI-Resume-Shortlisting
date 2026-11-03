from datetime import datetime, timezone, timedelta
import logging
from typing import Any
from pymongo import ReturnDocument

from app.config.settings import settings
from app.database.collections import MongoCollections
from app.database.mongodb import mongodb
from app.schemas.batch import Batch

logger = logging.getLogger(__name__)


class BatchRepository:
    """
    MongoDB repository for managing isolated recruitment batches / sessions.

    Tracks batch lifecycle, candidate file counts, active batch switching,
    retention expirations, and safe legacy data migration.
    """

    COLLECTION_NAME = MongoCollections.BATCHES

    def _collection(self):
        try:
            database = mongodb.get_database()
            if isinstance(database, dict):
                # In unit-test mock environments where database is a dictionary of mocks
                return database.get(self.COLLECTION_NAME)
            return database[self.COLLECTION_NAME]
        except RuntimeError:
            return None

    async def create_indexes(self) -> None:
        """
        Create necessary indexes for batch querying, status filtering, and retention.
        """
        try:
            col = self._collection()
            if col is None:
                return

            await col.create_index("batch_id", unique=True)
            await col.create_index("is_active")
            await col.create_index("status")
            await col.create_index("expires_at")
            await col.create_index([("is_active", 1), ("status", 1)])
            logger.info("Batch repository indexes initialized.")
        except Exception:
            logger.exception("Failed to create batch collection indexes.")

    async def save(self, batch: Batch) -> None:
        """
        Store or replace a batch document.
        """
        col = self._collection()
        if col is None:
            return

        doc = batch.model_dump(mode="json")
        doc["_id"] = batch.batch_id

        await col.replace_one(
            {"_id": doc["_id"]},
            doc,
            upsert=True,
        )

    async def get(self, batch_id: str) -> dict | None:
        """
        Retrieve a batch by its unique batch_id.
        """
        col = self._collection()
        if col is None:
            return None

        return await col.find_one({"_id": batch_id}) or await col.find_one({"batch_id": batch_id})

    async def get_active(self) -> dict | None:
        """
        Retrieve the single currently active candidate batch.
        Under the batch isolation rule, matching processes candidates strictly
        from the active batch.
        """
        col = self._collection()
        if col is None:
            return None

        return await col.find_one({"is_active": True})

    async def list_batches(
        self,
        limit: int = 50,
        skip: int = 0,
    ) -> list[dict]:
        """
        List all recruitment batches ordered by creation timestamp descending.
        """
        col = self._collection()
        if col is None:
            return []

        cursor = (
            col.find({})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count(self) -> int:
        """
        Return the total number of batches in MongoDB.
        """
        col = self._collection()
        if col is None:
            return 0
        return await col.count_documents({})

    async def activate(self, batch_id: str) -> dict:
        """
        Atomically switches the active recruitment batch to batch_id.

        Guarantees:
        - Any previously active batch is marked is_active=False, status='superseded',
          and given an expiration timestamp based on BATCH_RETENTION_HOURS.
        - The target batch is marked is_active=True, status='active', and expires_at=None.
        - Target batch must be in ['ready', 'active', 'superseded', 'processing'] status.
          Cancelled or expired batches cannot be activated.
        """
        col = self._collection()
        if col is None:
            raise RuntimeError("Database collection not available.")

        target = await self.get(batch_id)
        if not target:
            raise ValueError(f"Batch '{batch_id}' not found.")

        target_status = target.get("status")
        if target_status in ["cancelled", "expired", "failed", "draft"]:
            raise ValueError(
                f"Cannot activate batch '{batch_id}' with status '{target_status}'. "
                "Only ready, active, or superseded batches can be activated."
            )

        if target_status == "processing":
            total = target.get("total_files", 0)
            processed = target.get("processed_count", 0)
            completed = target.get("completed_count", 0)
            if total == 0 or processed < total or completed == 0:
                raise ValueError(
                    f"Cannot activate batch '{batch_id}' with status 'processing'. "
                    "The batch has not completed processing yet."
                )

        now = datetime.now(timezone.utc)
        retention_delta = timedelta(hours=settings.BATCH_RETENTION_HOURS)
        superseded_expiry = (now + retention_delta).isoformat()
        now_str = now.isoformat()

        # Step 1: Supersede all currently active batches
        await col.update_many(
            {"is_active": True},
            {
                "$set": {
                    "is_active": False,
                    "status": "superseded",
                    "expires_at": superseded_expiry,
                    "updated_at": now_str,
                    "last_activity_at": now_str,
                }
            },
        )

        # Step 2: Atomically mark the target batch as active
        updated_target = await col.find_one_and_update(
            {"_id": target["_id"]},
            {
                "$set": {
                    "is_active": True,
                    "status": "active",
                    "expires_at": None,
                    "updated_at": now_str,
                    "last_activity_at": now_str,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

        logger.info(
            "Batch '%s' successfully set as the active candidate batch.",
            batch_id,
        )
        return updated_target

    async def update_status(
        self,
        batch_id: str,
        status: str,
        total_files: int | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: str | None = None,
        clear_expires_at: bool = False,
    ) -> dict | None:
        """
        Update the status and optional metadata of a batch.
        Automatically stamps expires_at for terminal failed/cancelled states if not provided.
        """
        col = self._collection()
        if col is None:
            return None

        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        update_doc: dict[str, Any] = {
            "status": status,
            "updated_at": now_str,
            "last_activity_at": now_str,
        }
        if total_files is not None:
            update_doc["total_files"] = total_files

        if expires_at is not None:
            update_doc["expires_at"] = expires_at
        elif clear_expires_at or status == "active":
            update_doc["expires_at"] = None
        elif status in ["failed", "cancelled"] and not clear_expires_at:
            # Retention safety guard: failed and cancelled batches automatically receive an expiry timestamp
            retention_delta = timedelta(hours=settings.BATCH_RETENTION_HOURS)
            update_doc["expires_at"] = (now + retention_delta).isoformat()

        if metadata is not None:
            for k, v in metadata.items():
                update_doc[f"metadata.{k}"] = v

        return await col.find_one_and_update(
            {"$or": [{"_id": batch_id}, {"batch_id": batch_id}]},
            {"$set": update_doc},
            return_document=ReturnDocument.AFTER,
        )

    async def increment_progress(
        self,
        batch_id: str,
        completed: bool,
    ) -> dict | None:
        """
        Atomically increment processing counts and check for batch completion.
        """
        col = self._collection()
        if col is None:
            return None

        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        inc_fields: dict[str, int] = {"processed_count": 1}
        if completed:
            inc_fields["completed_count"] = 1
        else:
            inc_fields["failed_count"] = 1

        updated = await col.find_one_and_update(
            {"$or": [{"_id": batch_id}, {"batch_id": batch_id}]},
            {
                "$inc": inc_fields,
                "$set": {
                    "updated_at": now_str,
                    "last_activity_at": now_str,
                },
            },
            return_document=ReturnDocument.AFTER,
        )

        if not updated:
            return None

        total = updated.get("total_files", 0)
        processed = updated.get("processed_count", 0)
        current_status = updated.get("status")

        # When all files have finished processing
        if total > 0 and processed >= total and current_status == "processing":
            if updated.get("auto_activate", False) and updated.get("completed_count", 0) > 0:
                logger.info(
                    "Batch '%s' completed processing and auto_activate is enabled. Activating batch.",
                    batch_id,
                )
                return await self.activate(batch_id)
            else:
                retention_delta = timedelta(hours=settings.BATCH_RETENTION_HOURS)
                expires_at = (now + retention_delta).isoformat()
                final_status = "ready" if updated.get("completed_count", 0) > 0 else "failed"
                updated = await col.find_one_and_update(
                    {"_id": updated["_id"]},
                    {
                        "$set": {
                            "status": final_status,
                            "expires_at": expires_at,
                            "updated_at": now_str,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                )
                logger.info(
                    "Batch '%s' completed processing. Transitioned to status '%s'.",
                    batch_id,
                    final_status,
                )

        return updated

    async def cancel_batch(self, batch_id: str) -> dict | None:
        """
        Cancel a batch. Cancelled batches are never matched and in-flight worker
        jobs discard processing for cancelled batches.
        """
        col = self._collection()
        if col is None:
            return None

        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        retention_delta = timedelta(hours=settings.BATCH_RETENTION_HOURS)
        expires_at = (now + retention_delta).isoformat()

        return await col.find_one_and_update(
            {"$or": [{"_id": batch_id}, {"batch_id": batch_id}]},
            {
                "$set": {
                    "status": "cancelled",
                    "is_active": False,
                    "expires_at": expires_at,
                    "updated_at": now_str,
                    "last_activity_at": now_str,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def is_cancelled_or_expired(self, batch_id: str) -> bool:
        """
        Check if a batch is cancelled, expired, failed, or non-existent.
        In-flight worker jobs discard processing if this returns True.
        """
        batch = await self.get(batch_id)
        if not batch:
            return True
        return batch.get("status") in ["cancelled", "expired", "failed"]

    async def get_expired_batches(self, now: datetime) -> list[dict]:
        """
        Query all inactive batches whose retention period has expired.
        Strict rule: A batch marked is_active=True is NEVER returned as expired.
        Supports both ISO string and BSON datetime types.
        """
        col = self._collection()
        if col is None:
            return []

        now_iso = now.isoformat()
        cursor = col.find(
            {
                "is_active": False,
                "status": {"$in": ["superseded", "cancelled", "draft", "failed", "ready"]},
                "$or": [
                    {"expires_at": {"$ne": None, "$lte": now_iso}},
                    {"expires_at": {"$ne": None, "$lte": now}},
                ],
            }
        )
        return await cursor.to_list(length=None)

    async def delete(self, batch_id: str) -> None:
        """
        Delete a single batch document.
        """
        col = self._collection()
        if col is None:
            return
        await col.delete_one({"$or": [{"_id": batch_id}, {"batch_id": batch_id}]})

    async def record_cleanup_failure(
        self,
        batch_id: str,
        error_message: str,
    ) -> dict | None:
        """
        Record a filesystem cleanup failure and error metadata on an expired batch,
        retaining it for a subsequent retry while preserving data consistency.
        """
        col = self._collection()
        if col is None:
            return None

        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        update_doc = {
            "cleanup_pending": True,
            "cleanup_error": error_message,
            "cleanup_last_attempt_at": now_str,
            "updated_at": now_str,
        }

        try:
            return await col.find_one_and_update(
                {"$or": [{"_id": batch_id}, {"batch_id": batch_id}]},
                {
                    "$set": update_doc,
                    "$inc": {"cleanup_retry_count": 1},
                },
                return_document=ReturnDocument.AFTER,
            )
        except Exception:
            logger.exception("Failed to record cleanup failure for batch '%s'.", batch_id)
            return None


    async def ensure_legacy_batch_consistency(self) -> None:
        """
        Safe legacy-data migration:
        Inspects existing resumes and resume_embeddings for any upload_id values
        lacking a corresponding batch record.
        Creates a 'superseded' legacy batch record for each, ensuring:
        - Legacy data is preserved and never deleted.
        - Legacy data does not pollute new recruitment batches or matching.
        - Legacy records can be inspected or activated by administrators if desired.
        """
        try:
            database = mongodb.get_database()
            if database is None:
                return

            resumes_col = database[MongoCollections.RESUMES] if not isinstance(database, dict) else database.get(MongoCollections.RESUMES)
            embeddings_col = database[MongoCollections.RESUME_EMBEDDINGS] if not isinstance(database, dict) else database.get(MongoCollections.RESUME_EMBEDDINGS)
            batches_col = self._collection()
            if resumes_col is None or embeddings_col is None or batches_col is None:
                return

            resume_upload_ids = await resumes_col.distinct("upload_id")
            emb_upload_ids = await embeddings_col.distinct("upload_id")
            all_legacy_ids = set(resume_upload_ids) | set(emb_upload_ids)

            now = datetime.now(timezone.utc)
            for upload_id in all_legacy_ids:
                if not upload_id:
                    continue
                existing = await batches_col.find_one(
                    {"$or": [{"_id": upload_id}, {"batch_id": upload_id}]}
                )
                if not existing:
                    # Count associated records
                    r_count = await resumes_col.count_documents({"upload_id": upload_id})
                    legacy_batch = {
                        "_id": upload_id,
                        "batch_id": upload_id,
                        "batch_name": f"Legacy Upload ({upload_id[:8]})",
                        "status": "superseded",
                        "is_active": False,
                        "total_files": r_count,
                        "processed_count": r_count,
                        "completed_count": r_count,
                        "failed_count": 0,
                        "auto_activate": False,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "last_activity_at": now.isoformat(),
                        "expires_at": None,  # Legacy batches never auto-expire
                        "metadata": {"is_legacy": True},
                    }
                    await batches_col.replace_one(
                        {"_id": upload_id},
                        legacy_batch,
                        upsert=True,
                    )
                    logger.info(
                        "Created legacy batch wrapper for unbatched upload_id: %s",
                        upload_id,
                    )
        except Exception:
            logger.exception("Error during legacy batch consistency check.")


batch_repository = BatchRepository()
