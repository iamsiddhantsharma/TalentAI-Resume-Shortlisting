import asyncio

from app.database.mongodb import mongodb
from app.database.resume_repository import resume_repository
from app.database.resume_embedding_repository import (
    resume_embedding_repository,
)

from app.services.resume_embedding_generation_service import (
    resume_embedding_generation_service,
)


async def main():

    print("=" * 70)
    print("RESUME EMBEDDING GENERATION TEST")
    print("=" * 70)

    await mongodb.connect()

    try:

        # ---------------------------------------------------------
        # 1. Find an existing processed resume
        # ---------------------------------------------------------

        resumes = await resume_repository.get_all()

        completed_resumes = [
            resume
            for resume in resumes
            if resume.get("status") == "completed"
            and resume.get("resume_data") is not None
        ]

        if not completed_resumes:
            print(
                "\nERROR: No completed resume with "
                "structured data found in MongoDB."
            )
            print(
                "Process at least one resume before "
                "running this test."
            )
            return

        resume = completed_resumes[-1]

        upload_id = resume.get("upload_id")
        filename = resume.get("filename")

        if not upload_id or not filename:
            print(
                "\nERROR: Selected resume is missing "
                "upload_id or filename."
            )
            return

        print(f"\nResume found: {filename}")
        print(f"Upload ID: {upload_id}")

        # ---------------------------------------------------------
        # 2. Generate and save embeddings
        # ---------------------------------------------------------

        result = (
            await resume_embedding_generation_service
            .generate_for_resume(
                upload_id=upload_id,
                filename=filename,
            )
        )

        print("\nGeneration result:")
        print(result)

        if result.get("evidence_count", 0) <= 0:
            print("\nERROR: No evidence was generated.")
            return

        if result.get("embedding_count", 0) <= 0:
            print("\nERROR: No embeddings were generated.")
            return

        if result.get("embedding_dimension") != 1024:
            print(
                "\nERROR: Embedding dimension is not 1024: "
                f"{result.get('embedding_dimension')}"
            )
            return

        # ---------------------------------------------------------
        # 3. Verify MongoDB storage
        # ---------------------------------------------------------

        stored = await resume_embedding_repository.get(
            upload_id=upload_id,
            filename=filename,
        )

        if stored is None:
            print(
                "\nERROR: Embeddings were not found "
                "after generation."
            )
            return

        embeddings = stored.get(
            "embeddings",
            [],
        )

        print(
            f"\nStored resume embeddings: "
            f"{len(embeddings)}"
        )

        if not embeddings:
            print(
                "\nERROR: Embedding document exists "
                "but contains no embeddings."
            )
            return

        print(
            "Embedding dimension:",
            len(embeddings[0]["embedding"]),
        )

        print(
            "Stored upload_id:",
            stored.get("upload_id"),
        )

        print(
            "Stored filename:",
            stored.get("filename"),
        )

        if stored.get("upload_id") != upload_id:
            print(
                "\nERROR: Stored upload_id does not match."
            )
            return

        if stored.get("filename") != filename:
            print(
                "\nERROR: Stored filename does not match."
            )
            return

        if len(embeddings[0]["embedding"]) != 1024:
            print(
                "\nERROR: Stored embedding dimension "
                "is not 1024."
            )
            return

        print(
            "\nSUCCESS: Resume embeddings "
            "are stored in MongoDB."
        )

    finally:

        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
