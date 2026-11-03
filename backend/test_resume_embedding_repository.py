import asyncio

from app.database.mongodb import mongodb
from app.database.resume_embedding_repository import (
    resume_embedding_repository,
)


async def main():

    # ------------------------------------------------------
    # CONNECT TO MONGODB
    # ------------------------------------------------------

    await mongodb.connect()

    print("\nMongoDB connected successfully.")

    try:

        # --------------------------------------------------
        # TEST DATA
        # --------------------------------------------------

        embeddings = [
            {
                "source_type": "resume",
                "section": "skills",
                "item_index": 0,
                "text": "Skill: Python",
                "embedding": [0.1] * 1024,
            },
            {
                "source_type": "resume",
                "section": "skills",
                "item_index": 1,
                "text": "Skill: Machine Learning",
                "embedding": [0.2] * 1024,
            },
            {
                "source_type": "resume",
                "section": "projects",
                "item_index": 0,
                "text": "Project: AI Resume Shortlister",
                "embedding": [0.3] * 1024,
            },
        ]

        upload_id = "test_resume_001"
        filename = "siddhant_test_resume.pdf"

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------

        await resume_embedding_repository.save(
            upload_id=upload_id,
            filename=filename,
            embeddings=embeddings,
        )

        print("\nResume embeddings saved successfully.")

        # --------------------------------------------------
        # GET
        # --------------------------------------------------

        document = await resume_embedding_repository.get(
            upload_id=upload_id,
            filename=filename,
        )

        if document is None:
            print("\nERROR: Document was not found.")
            return

        # --------------------------------------------------
        # VERIFY
        # --------------------------------------------------

        print("\nRetrieved document successfully.")

        print("\n----------------------------------------")

        print("Upload ID:")
        print(document["upload_id"])

        print("\nFilename:")
        print(document["filename"])

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
        # COUNT
        # --------------------------------------------------

        count = await resume_embedding_repository.count()

        print("\nResume embedding documents in MongoDB:")
        print(count)

    finally:

        # --------------------------------------------------
        # DISCONNECT
        # --------------------------------------------------

        await mongodb.disconnect()

        print("\nMongoDB disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
