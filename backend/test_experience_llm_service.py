import asyncio

from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.resume_object import (
    Experience,
    ResumeObject,
)
from app.services.experience_llm_service import (
    experience_llm_service,
)


# ======================================================
# TEST 1: RELEVANT + IRRELEVANT EXPERIENCES
# ======================================================

async def test_relevant_and_irrelevant_experience():
    print("\n" + "=" * 70)
    print("TEST 1: RELEVANT AND IRRELEVANT EXPERIENCE")
    print("=" * 70)

    # --------------------------------------------------
    # JOB DESCRIPTION
    # --------------------------------------------------

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
            "SQL",
            "REST APIs",
        ],
        responsibilities=[
            "Develop and maintain banking software systems",
            "Build payment processing services",
            "Work with financial data and banking APIs",
        ],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2,
                maximum_years=5,
                preferred_domains=[
                    "Financial Services",
                    "Banking Technology",
                ],
            )
        ],
        tools_and_technologies=[
            "Python",
            "SQL",
            "REST APIs",
        ],
    )

    # --------------------------------------------------
    # RESUME
    # --------------------------------------------------

    resume = ResumeObject(
        name="Test Candidate",
        experience=[
            Experience(
                company="ABC Banking Technologies",
                role="Software Engineer",
                start_date="2021-01",
                end_date="2024-01",
                description=(
                    "Developed payment processing services "
                    "using Python and REST APIs for banking "
                    "customers. Worked with financial data "
                    "and banking platforms."
                ),
            ),
            Experience(
                company="Creative Design Studio",
                role="Graphic Designer",
                start_date="2020-01",
                end_date="2022-01",
                description=(
                    "Designed branding materials, social media "
                    "graphics, brochures, and marketing artwork "
                    "for clients."
                ),
            ),
        ],
    )

    # --------------------------------------------------
    # CALL QWEN
    # --------------------------------------------------

    result = (
        await experience_llm_service.evaluate_experiences(
            job_description=job_description,
            resume=resume,
        )
    )

    # --------------------------------------------------
    # PRINT RESULT
    # --------------------------------------------------

    print("\nQWEN RESULT:\n")

    for decision in result.experience_decisions:

        print(
            f"Experience Index : "
            f"{decision.experience_index}"
        )

        print(
            f"Decision         : "
            f"{decision.decision}"
        )

        print(
            f"Matched Domains  : "
            f"{decision.matched_domains}"
        )

        print(
            f"Matched Context  : "
            f"{decision.matched_context}"
        )

        print(
            f"Reason           : "
            f"{decision.reason}"
        )

        print("-" * 70)

    # --------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------

    assert len(
        result.experience_decisions
    ) == 2

    indexes = {
        decision.experience_index
        for decision in result.experience_decisions
    }

    assert indexes == {0, 1}

    print("\nTEST 1 PASSED")


# ======================================================
# TEST 2: INSUFFICIENT INFORMATION
# ======================================================

async def test_insufficient_information():
    print("\n" + "=" * 70)
    print("TEST 2: INSUFFICIENT INFORMATION")
    print("=" * 70)

    # --------------------------------------------------
    # JOB DESCRIPTION
    # --------------------------------------------------

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
            "SQL",
        ],
        responsibilities=[
            "Develop financial data processing systems",
        ],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2,
                preferred_domains=[
                    "Financial Services",
                ],
            )
        ],
        tools_and_technologies=[
            "Python",
            "SQL",
        ],
    )

    # --------------------------------------------------
    # RESUME
    # --------------------------------------------------

    resume = ResumeObject(
        name="Test Candidate",
        experience=[
            Experience(
                company="ABC Company",
                role="Analyst",
                start_date=None,
                end_date=None,
                description="Worked on various tasks.",
            ),
        ],
    )

    # --------------------------------------------------
    # CALL QWEN
    # --------------------------------------------------

    result = (
        await experience_llm_service.evaluate_experiences(
            job_description=job_description,
            resume=resume,
        )
    )

    # --------------------------------------------------
    # PRINT
    # --------------------------------------------------

    print("\nQWEN RESULT:\n")

    for decision in result.experience_decisions:

        print(
            f"Experience Index : "
            f"{decision.experience_index}"
        )

        print(
            f"Decision         : "
            f"{decision.decision}"
        )

        print(
            f"Reason           : "
            f"{decision.reason}"
        )

        print("-" * 70)

    # --------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------

    assert len(
        result.experience_decisions
    ) == 1

    assert (
        result.experience_decisions[0]
        .experience_index
        == 0
    )

    print("\nTEST 2 PASSED")


# ======================================================
# TEST 3: FRESHER / NO EXPERIENCE REQUIREMENT
# ======================================================

async def test_fresher_jd_skips_qwen():
    print("\n" + "=" * 70)
    print("TEST 3: FRESHER JD - QWEN SHOULD BE SKIPPED")
    print("=" * 70)

    # --------------------------------------------------
    # FRESHER JOB DESCRIPTION
    # --------------------------------------------------

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
            "SQL",
        ],
        responsibilities=[
            "Assist with data analysis",
            "Build basic data processing solutions",
        ],
        experience_requirements=[],
        tools_and_technologies=[
            "Python",
            "SQL",
        ],
    )

    # --------------------------------------------------
    # RESUME
    # --------------------------------------------------

    resume = ResumeObject(
        name="Fresher Candidate",
        experience=[],
    )

    # --------------------------------------------------
    # CALL SERVICE
    # --------------------------------------------------

    result = (
        await experience_llm_service.evaluate_experiences(
            job_description=job_description,
            resume=resume,
        )
    )

    # --------------------------------------------------
    # QWEN SHOULD NOT BE CALLED
    # --------------------------------------------------

    assert (
        result.experience_decisions == []
    )

    print(
        "\nQwen was correctly skipped."
    )

    print("\nTEST 3 PASSED")


# ======================================================
# TEST 4: EMPTY EXPERIENCE REQUIREMENT OBJECT
# ======================================================

async def test_empty_experience_requirement_skips_qwen():
    print("\n" + "=" * 70)
    print(
        "TEST 4: EMPTY EXPERIENCE REQUIREMENT "
        "- QWEN SHOULD BE SKIPPED"
    )
    print("=" * 70)

    # --------------------------------------------------
    # JD WITH EMPTY EXPERIENCE OBJECT
    # --------------------------------------------------

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
        ],
        responsibilities=[
            "Develop software applications",
        ],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=None,
                maximum_years=None,
                preferred_domains=[],
            )
        ],
        tools_and_technologies=[
            "Python",
        ],
    )

    # --------------------------------------------------
    # RESUME
    # --------------------------------------------------

    resume = ResumeObject(
        name="Test Candidate",
        experience=[
            Experience(
                company="ABC Company",
                role="Software Engineer",
                start_date="2022-01",
                end_date="2024-01",
                description=(
                    "Developed software applications."
                ),
            ),
        ],
    )

    # --------------------------------------------------
    # CALL SERVICE
    # --------------------------------------------------

    result = (
        await experience_llm_service.evaluate_experiences(
            job_description=job_description,
            resume=resume,
        )
    )

    # --------------------------------------------------
    # QWEN SHOULD BE SKIPPED
    # --------------------------------------------------

    assert (
        result.experience_decisions == []
    )

    print(
        "\nQwen was correctly skipped for an "
        "empty experience requirement."
    )

    print("\nTEST 4 PASSED")


# ======================================================
# MAIN
# ======================================================

async def main():

    await test_relevant_and_irrelevant_experience()

    await test_insufficient_information()

    await test_fresher_jd_skips_qwen()

    await test_empty_experience_requirement_skips_qwen()

    print("\n" + "=" * 70)
    print("ALL EXPERIENCE LLM TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
