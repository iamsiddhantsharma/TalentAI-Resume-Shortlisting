import asyncio

from app.services.extraction_recovery import (
    extraction_recovery_service,
)


async def main():
    print("=" * 60)
    print("PHASE 5.7 - ERROR RECOVERY TEST")
    print("=" * 60)

    # --------------------------------------------------
    # Resume recovery test
    # --------------------------------------------------

    resume_text = """
    Siddhant Sharma is a B.Tech student specializing in
    Internet of Things Engineering. He is skilled in Python,
    C++, FastAPI and MongoDB. He developed an AI Resume
    Shortlister using Python and FastAPI.
    """

    print("\nTesting resume recovery...")

    resume = (
        await extraction_recovery_service.extract_resume(
            resume_text
        )
    )

    print("\n========== RESUME RESULT ==========")
    print(resume.model_dump())

    assert resume.name is not None
    assert len(resume.skills) > 0
    assert isinstance(resume.skills, list)

    print("\n✓ Resume extraction returned a valid ResumeObject")
    print("✓ Resume schema validation passed")

    # --------------------------------------------------
    # Job Description recovery test
    # --------------------------------------------------

    jd_text = """
    We are looking for a Backend Software Engineer with
    experience in Python, FastAPI and MongoDB. The candidate
    should have one to three years of software development
    experience. Experience with Docker and AWS is preferred.
    The role involves developing REST APIs and backend services.
    """

    print("\nTesting JD recovery...")

    jd = (
        await extraction_recovery_service
        .extract_job_description(
            jd_text
        )
    )

    print("\n========== JD RESULT ==========")
    print(jd.model_dump())

    # --------------------------------------------------
    # JD schema validation
    # --------------------------------------------------

    assert jd.job_title is not None

    assert (
        jd.minimum_experience_years == 1
    )

    assert (
        jd.maximum_experience_years == 3
    )

    assert isinstance(
        jd.required_skills,
        list,
    )

    assert isinstance(
        jd.preferred_skills,
        list,
    )

    assert isinstance(
        jd.skill_experience_requirements,
        list,
    )

    assert isinstance(
        jd.responsibilities,
        list,
    )

    # --------------------------------------------------
    # Verify every skill-experience item is an object
    # --------------------------------------------------

    for requirement in (
        jd.skill_experience_requirements
    ):

        assert requirement.skill

        assert requirement.importance in (
            "required",
            "preferred",
        )

        assert (
            requirement.minimum_years is None
            or isinstance(
                requirement.minimum_years,
                float,
            )
        )

        assert (
            requirement.maximum_years is None
            or isinstance(
                requirement.maximum_years,
                float,
            )
        )

    print(
        "\n✓ JD extraction returned a valid "
        "JobDescriptionObject"
    )

    print("✓ JD schema validation passed")
    print(
        "✓ Skill experience requirements have "
        "correct object structure"
    )

    print("\n" + "=" * 60)
    print("PHASE 5.7 RECOVERY TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
