import logging

from app.database.batch_repository import (
    batch_repository,
)
from app.database.jd_repository import (
    jd_repository,
)
from app.database.resume_embedding_repository import (
    resume_embedding_repository,
)
from app.database.resume_repository import (
    resume_repository,
)
from app.services.result_store import (
    result_store,
)
from app.services.storage_service import (
    storage_service,
)


logger = logging.getLogger(__name__)


class PrivacyService:
    """
    Centralized privacy cleanup service.

    Manual development/testing reset only.
    NEVER executed on normal shutdown or restart.
    """

    async def clear_all_data(
        self,
    ) -> None:
        """
        Remove all temporary TalentAI data.
        """

        logger.info(
            "Starting privacy cleanup..."
        )

        # ----------------------------------------------------
        # 1. MongoDB
        # ----------------------------------------------------

        try:

            await resume_repository.delete_all()
            await resume_embedding_repository.delete_all()
            batch_col = batch_repository._collection()
            if batch_col is not None:
                await batch_col.delete_many({})

            logger.info(
                "MongoDB resume and batch data deleted."
            )

        except Exception:

            logger.exception(
                "Failed to delete resume data from MongoDB."
            )

        try:

            await jd_repository.delete_all()

            logger.info(
                "MongoDB Job Description data deleted."
            )

        except Exception:

            logger.exception(
                "Failed to delete Job Description data from MongoDB."
            )

        # ----------------------------------------------------
        # 2. In-memory ResultStore
        # ----------------------------------------------------

        try:

            result_store.clear()

            logger.info(
                "In-memory ResultStore cleared."
            )

        except Exception:

            logger.exception(
                "Failed to clear ResultStore."
            )

        # ----------------------------------------------------
        # 3. Local filesystem
        # ----------------------------------------------------

        try:

            storage_service.clear_temporary_storage()

            logger.info(
                "Temporary filesystem data deleted."
            )

        except Exception:

            logger.exception(
                "Failed to clear temporary filesystem data."
            )

        logger.info(
            "Privacy cleanup completed."
        )


privacy_service = PrivacyService()
