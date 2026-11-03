import asyncio

from app.database.mongodb import mongodb
from app.database.jd_repository import jd_repository
from app.database.jd_embedding_repository import (
    jd_embedding_repository,
)
from app.database.resume_repository import resume_repository
from app.database.resume_embedding_repository import (
    resume_embedding_repository,
)

from app.schemas.job_description import JobDescription
from app.schemas.job_description_object import (
    JobDescriptionObject,
    ExperienceRequirement,
)

from app.services.jd_embedding_generation_service import (
    job_description_embedding_generation_service,
)
from app.services.result_store import result_store


def build_jd(
    jd_id: str,
    skill: str,
) -> JobDescription:
    """
    Build a minimal valid JobDescription for persistence tests.
    """

    return JobDescription(
        jd_id=jd_id,
        input_type="text",
        filename=None,
        file_extension=None,
        raw_text=f"Looking for a {skill} developer.",
        status="completed",
        structured_data=JobDescriptionObject(
            required_skills=[skill],
            responsibilities=[
                f"Build systems using {skill}."
            ],
            experience_requirements=[
                ExperienceRequirement(
                    minimum_years=2,
                    maximum_years=5,
                    preferred_domains=["software"],
                )
            ],
            tools_and_technologies=[skill],
        ),
        error=None,
    )


async def main():

    print("=" * 70)
    print("ONE JD RULE TEST")
    print("=" * 70)

    await mongodb.connect()

    try:

        # ---------------------------------------------------------
        # Baseline: resume counts must remain unchanged
        # ---------------------------------------------------------

        resume_count_before = await resume_repository.count()
        resume_embedding_count_before = (
            await resume_embedding_repository.count()
        )

        print(f"\nResume count before: {resume_count_before}")
        print(
            "Resume embedding count before: "
            f"{resume_embedding_count_before}"
        )

        # ---------------------------------------------------------
        # 1. Process / store JD A
        # ---------------------------------------------------------

        jd_a = build_jd(
            jd_id="11111111-1111-1111-1111-111111111111",
            skill="Python",
        )

        result_store.save_job_description(jd_a)
        await jd_repository.save(jd_a)

        await job_description_embedding_generation_service.generate_for_jd(
            jd_a.jd_id
        )

        jd_count_after_a = await jd_repository.count()
        stored_after_a = await jd_repository.get_all()
        active_after_a = await jd_embedding_repository.get()

        print(f"\nAfter JD A:")
        print(f"job_descriptions count: {jd_count_after_a}")
        print(
            "stored jd_id:",
            stored_after_a[0].get("jd_id")
            if stored_after_a
            else None,
        )
        print(
            "active_jd jd_id:",
            active_after_a.get("jd_id")
            if active_after_a
            else None,
        )

        if jd_count_after_a != 1:
            print("\nERROR: Expected exactly 1 JD after JD A.")
            return

        if stored_after_a[0].get("jd_id") != jd_a.jd_id:
            print("\nERROR: JD A was not stored correctly.")
            return

        if (
            active_after_a is None
            or active_after_a.get("jd_id") != jd_a.jd_id
        ):
            print(
                "\nERROR: active_jd does not point to JD A."
            )
            return

        # ---------------------------------------------------------
        # 2. Process / store JD B (must replace JD A)
        # ---------------------------------------------------------

        jd_b = build_jd(
            jd_id="22222222-2222-2222-2222-222222222222",
            skill="Java",
        )

        result_store.save_job_description(jd_b)
        await jd_repository.save(jd_b)

        # After replace, old embeddings are cleared until
        # the new JD embeddings are generated.
        stale_active = await jd_embedding_repository.get()
        if stale_active is not None:
            print(
                "\nERROR: Old active_jd embeddings were "
                "not cleared when JD B was saved."
            )
            return

        await job_description_embedding_generation_service.generate_for_jd(
            jd_b.jd_id
        )

        jd_count_after_b = await jd_repository.count()
        stored_after_b = await jd_repository.get_all()
        active_after_b = await jd_embedding_repository.get()
        jd_a_lookup = await jd_repository.get(jd_a.jd_id)
        jd_b_lookup = await jd_repository.get(jd_b.jd_id)

        resume_count_after = await resume_repository.count()
        resume_embedding_count_after = (
            await resume_embedding_repository.count()
        )
        in_memory_count = result_store.count_job_descriptions()

        print(f"\nAfter JD B:")
        print(f"job_descriptions count: {jd_count_after_b}")
        print(
            "stored jd_id:",
            stored_after_b[0].get("jd_id")
            if stored_after_b
            else None,
        )
        print(
            "active_jd jd_id:",
            active_after_b.get("jd_id")
            if active_after_b
            else None,
        )
        print(f"JD A still present: {jd_a_lookup is not None}")
        print(f"JD B present: {jd_b_lookup is not None}")
        print(f"Resume count after: {resume_count_after}")
        print(
            "Resume embedding count after: "
            f"{resume_embedding_count_after}"
        )
        print(f"In-memory JD count: {in_memory_count}")

        # ---------------------------------------------------------
        # 3. Assertions
        # ---------------------------------------------------------

        errors = []

        if jd_count_after_b != 1:
            errors.append(
                "Expected exactly 1 JD after JD B."
            )

        if jd_a_lookup is not None:
            errors.append("JD A was not deleted.")

        if jd_b_lookup is None:
            errors.append("JD B was not stored.")

        if (
            not stored_after_b
            or stored_after_b[0].get("jd_id") != jd_b.jd_id
        ):
            errors.append(
                "Stored JD is not JD B."
            )

        if (
            active_after_b is None
            or active_after_b.get("jd_id") != jd_b.jd_id
        ):
            errors.append(
                "active_jd does not point to JD B."
            )

        if resume_count_after != resume_count_before:
            errors.append(
                "Resume count changed after JD replacement."
            )

        if (
            resume_embedding_count_after
            != resume_embedding_count_before
        ):
            errors.append(
                "Resume embedding count changed after "
                "JD replacement."
            )

        if in_memory_count != 1:
            errors.append(
                "In-memory ResultStore does not contain "
                "exactly one JD."
            )

        if errors:
            print("\nERROR:")
            for error in errors:
                print(f"- {error}")
            return

        print(
            "\nSUCCESS: One-JD rule enforced. "
            "Resumes preserved. active_jd points to JD B."
        )

    finally:

        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
