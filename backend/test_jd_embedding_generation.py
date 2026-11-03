import asyncio

from app.database.mongodb import mongodb
from app.database.jd_repository import jd_repository
from app.database.jd_embedding_repository import (
    jd_embedding_repository,
)

from app.services.jd_embedding_generation_service import (
    job_description_embedding_generation_service,
)


async def main():

    print("=" * 70)
    print("JD EMBEDDING GENERATION TEST")
    print("=" * 70)

    await mongodb.connect()

    try:

        # ---------------------------------------------------------
        # 1. Verify the active (only) JD exists
        # ---------------------------------------------------------

        job_descriptions = await jd_repository.get_all()

        if not job_descriptions:
            print("\nERROR: No job description found in MongoDB.")
            return

        if len(job_descriptions) != 1:
            print(
                "\nERROR: Expected exactly one JD, found "
                f"{len(job_descriptions)}."
            )
            return

        jd = job_descriptions[0]
        jd_id = jd.get("jd_id") or jd.get("_id")

        if not jd_id:
            print("\nERROR: Stored JD is missing jd_id.")
            return

        print(f"\nJD found: {jd_id}")

        # ---------------------------------------------------------
        # 2. Generate and save embeddings
        # ---------------------------------------------------------

        result = (
            await job_description_embedding_generation_service
            .generate_for_jd(jd_id)
        )

        print("\nGeneration result:")
        print(result)

        # ---------------------------------------------------------
        # 3. Verify MongoDB storage
        # ---------------------------------------------------------

        stored = (
            await jd_embedding_repository
            .get_by_jd_id(jd_id)
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
            f"\nStored JD embeddings: "
            f"{len(embeddings)}"
        )

        if embeddings:

            print(
                "Embedding dimension:",
                len(embeddings[0]["embedding"]),
            )

            print(
                "Stored JD ID:",
                stored.get("jd_id"),
            )

            print(
                "\nSUCCESS: JD embeddings "
                "are stored in MongoDB."
            )

        else:
            print(
                "\nERROR: Embedding document exists "
                "but contains no embeddings."
            )

    finally:

        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
