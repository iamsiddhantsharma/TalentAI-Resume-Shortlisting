import asyncio

from app.database.mongodb import mongodb
from app.database.jd_embedding_repository import (
    jd_embedding_repository,
)


async def main():

    # ------------------------------------------------------
    # CONNECT TO MONGODB
    # ------------------------------------------------------

    await mongodb.connect()

    try:

        # --------------------------------------------------
        # TEST JD EMBEDDINGS
        # --------------------------------------------------

        embeddings = [
            {
                "source_type": "job_description",
                "section": "required_skills",
                "item_index": 0,
                "text": "Required skill: Machine Learning",
                "embedding": [0.1] * 1024,
            },
            {
                "source_type": "job_description",
                "section": "responsibilities",
                "item_index": 0,
                "text": (
                    "Responsibility: Develop and optimize "
                    "machine learning models"
                ),
                "embedding": [0.2] * 1024,
            },
            {
                "source_type": "job_description",
                "section": "tools_and_technologies",
                "item_index": 0,
                "text": "Tool or technology: Python",
                "embedding": [0.3] * 1024,
            },
        ]

        jd_id = "test_jd_001"

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------

        await jd_embedding_repository.save(
            jd_id=jd_id,
            embeddings=embeddings,
        )

        print("\nJD embeddings saved successfully.")

        # --------------------------------------------------
        # GET
        # --------------------------------------------------

        document = await jd_embedding_repository.get()

        if document is None:
            print("\nERROR: JD embedding document not found.")
            return

        print("\nRetrieved JD embedding document successfully.")

        # --------------------------------------------------
        # VERIFY
        # --------------------------------------------------

        print("\n----------------------------------------")

        print("JD ID:")
        print(document["jd_id"])

        print("\nNumber of embeddings:")
        print(len(document["embeddings"]))

        print("\nFirst evidence:")
        print(document["embeddings"][0]["text"])

        print("\nFirst embedding dimension:")
        print(
            len(
                document["embeddings"][0]["embedding"]
            )
        )

        print("\n----------------------------------------")

        # --------------------------------------------------
        # VERIFY JD ID LOOKUP
        # --------------------------------------------------

        matching_document = (
            await jd_embedding_repository.get_by_jd_id(
                jd_id
            )
        )

        if matching_document is not None:
            print(
                "\nJD ID lookup successful."
            )
        else:
            print(
                "\nERROR: JD ID lookup failed."
            )

        # --------------------------------------------------
        # COUNT
        # --------------------------------------------------

        count = await jd_embedding_repository.count()

        print("\nJD embedding documents in MongoDB:")
        print(count)

        print("\n========================================")
        print("JD EMBEDDING REPOSITORY TEST PASSED")
        print("========================================")

    finally:

        # --------------------------------------------------
        # DISCONNECT
        # --------------------------------------------------

        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
