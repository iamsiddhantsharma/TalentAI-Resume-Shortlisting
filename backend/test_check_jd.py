import asyncio

from app.database.mongodb import mongodb
from app.database.jd_repository import jd_repository


async def main():
    print("=" * 70)
    print("CHECK STORED JOB DESCRIPTIONS")
    print("=" * 70)

    await mongodb.connect()

    try:
        database = mongodb.get_database()

        print("\nDatabase:")
        print(database.name)

        print("\nCollections:")
        print(await database.list_collection_names())

        job_descriptions = await jd_repository.get_all()

        print(
            f"\nJob descriptions found: "
            f"{len(job_descriptions)}"
        )

        for index, jd in enumerate(job_descriptions, start=1):

            print("\n" + "-" * 70)
            print(f"JD #{index}")

            print("_id:")
            print(jd.get("_id"))

            print("\njd_id:")
            print(jd.get("jd_id"))

            print("\nstatus:")
            print(jd.get("status"))

            print("\nfilename:")
            print(jd.get("filename"))

    finally:
        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
