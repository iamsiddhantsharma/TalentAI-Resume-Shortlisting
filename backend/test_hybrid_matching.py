import asyncio
import json

from app.database.mongodb import mongodb
from app.database.jd_repository import jd_repository
from app.database.resume_repository import resume_repository
from app.database.jd_embedding_repository import jd_embedding_repository
from app.database.resume_embedding_repository import resume_embedding_repository
from app.services.hybrid_matching_service import hybrid_matching_service


async def main():
    print("=" * 70)
    print("HYBRID MATCHING SERVICE TEST")
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. Connect to MongoDB
    # ---------------------------------------------------------

    await mongodb.connect()

    try:
        # -----------------------------------------------------
        # 2. Get all stored Job Descriptions
        # -----------------------------------------------------

        job_descriptions = await jd_repository.get_all()

        if not job_descriptions:
            print("\nERROR: No job descriptions found in MongoDB.")
            return

        print(f"\nJob descriptions found: {len(job_descriptions)}")

        # Use the latest/last stored JD
        jd_document = job_descriptions[-1]

        jd_id = jd_document["_id"]

        print(f"Using JD ID: {jd_id}")

        # -----------------------------------------------------
        # 3. Verify JD embeddings exist
        # -----------------------------------------------------

        jd_embedding_document = (
            await jd_embedding_repository.get_by_jd_id(jd_id)
        )

        if jd_embedding_document is None:
            print(
                f"\nERROR: No embeddings found for JD '{jd_id}'."
            )
            return

        jd_embeddings = jd_embedding_document.get(
            "embeddings",
            [],
        )

        print(
            f"JD evidence embeddings: {len(jd_embeddings)}"
        )

        if not jd_embeddings:
            print("\nERROR: JD has no evidence embeddings.")
            return

        # -----------------------------------------------------
        # 4. Get all stored resumes
        # -----------------------------------------------------

        resumes = await resume_repository.get_all()

        if not resumes:
            print("\nERROR: No resumes found in MongoDB.")
            return

        print(f"Resumes found: {len(resumes)}")

        # -----------------------------------------------------
        # 5. Find a resume that has embeddings
        # -----------------------------------------------------

        selected_resume = None

        for resume in resumes:
            upload_id = resume.get("upload_id")
            filename = resume.get("filename")

            if not upload_id or not filename:
                continue

            embedding_document = (
                await resume_embedding_repository.get(
                    upload_id=upload_id,
                    filename=filename,
                )
            )

            if embedding_document is None:
                continue

            embeddings = embedding_document.get(
                "embeddings",
                [],
            )

            if embeddings:
                selected_resume = resume
                break

        if selected_resume is None:
            print(
                "\nERROR: No resume with stored embeddings found."
            )
            return

        upload_id = selected_resume["upload_id"]
        filename = selected_resume["filename"]

        print(f"\nUsing resume: {filename}")
        print(f"Upload ID: {upload_id}")

        # -----------------------------------------------------
        # 6. Run Hybrid Matching
        # -----------------------------------------------------

        print("\n" + "-" * 70)
        print("RUNNING HYBRID MATCHING")
        print("-" * 70)

        result = await hybrid_matching_service.match_resume(
            jd_id=jd_id,
            upload_id=upload_id,
            filename=filename,
        )

        # -----------------------------------------------------
        # 7. Display result
        # -----------------------------------------------------

        print("\n" + "=" * 70)
        print("HYBRID MATCHING RESULT")
        print("=" * 70)

        print(
            json.dumps(
                result,
                indent=4,
                default=str,
            )
        )

        # -----------------------------------------------------
        # 8. Basic validation
        # -----------------------------------------------------

        print("\n" + "=" * 70)
        print("BASIC VALIDATION")
        print("=" * 70)

        required_keys = [
            "jd_id",
            "upload_id",
            "filename",
            "exact_matching",
            "semantic_retrieval",
            "experience_matching",
        ]

        for key in required_keys:
            if key in result:
                print(f"[PASS] {key}")
            else:
                print(f"[FAIL] {key}")

        # -----------------------------------------------------
        # 9. Validate semantic retrieval
        # -----------------------------------------------------

        semantic_results = result[
            "semantic_retrieval"
        ]["results"]

        print(
            f"\nSemantic retrieval results: "
            f"{len(semantic_results)}"
        )

        if semantic_results:
            print("[PASS] Semantic retrieval produced results.")
        else:
            print(
                "[WARNING] Semantic retrieval produced "
                "no results."
            )

        # -----------------------------------------------------
        # 10. Validate exact matching
        # -----------------------------------------------------

        exact_result = result["exact_matching"]

        print("\nExact matching:")

        print(
            "Required skills:",
            exact_result.get(
                "total_required_skills",
                0,
            ),
        )

        print(
            "Matched skills:",
            exact_result.get(
                "matched_required_skills",
                0,
            ),
        )

        print(
            "Unmatched skills:",
            exact_result.get(
                "unmatched_required_skills",
                0,
            ),
        )

        # -----------------------------------------------------
        # 11. Validate experience matching
        # -----------------------------------------------------

        experience_result = result[
            "experience_matching"
        ]

        print("\nExperience matching:")

        print(
            "Requirement present:",
            experience_result.get(
                "experience_requirement_present"
            ),
        )

        print(
            "Relevant experience found:",
            experience_result.get(
                "relevant_experience_found"
            ),
        )

        print(
            "Relevant duration:",
            experience_result.get(
                "relevant_duration_years"
            ),
        )

        print(
            "Minimum satisfied:",
            experience_result.get(
                "minimum_duration_satisfied"
            ),
        )

        print(
            "Maximum exceeded:",
            experience_result.get(
                "maximum_duration_exceeded"
            ),
        )

        print("\n" + "=" * 70)
        print("HYBRID MATCHING TEST COMPLETED")
        print("=" * 70)

    finally:
        # ---------------------------------------------------------
        # 12. Disconnect MongoDB
        # ---------------------------------------------------------

        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
