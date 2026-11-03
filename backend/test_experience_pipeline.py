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
from app.services.experience_matching_service import (
    experience_matching_service,
)


# ======================================================
# TEST 1
# QWEN RELEVANCE DETECTION + MATCHING INTEGRATION
# ======================================================

async def test_qwen_relevance_integration():
    print("\n" + "=" * 70)
    print("TEST 1: QWEN RELEVANCE DETECTION")
    print("=" * 70)

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
            "SQL",
            "REST APIs",
        ],
        responsibilities=[
            "Develop banking software systems",
            "Build payment processing services",
            "Work with financial data",
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
                    "graphics, brochures and marketing artwork."
                ),
            ),
        ],
    )

    # --------------------------------------------------
    # QWEN IS USED ONLY HERE
    # --------------------------------------------------

    relevance_result = (
        await experience_llm_service.evaluate_experiences(
            job_description=job_description,
            resume=resume,
        )
    )

    print("\nQWEN DECISIONS:\n")

    for decision in (
        relevance_result.experience_decisions
    ):
        print(
            f"Experience {decision.experience_index}: "
            f"{decision.decision}"
        )

        print(
            f"Reason: {decision.reason}"
        )

        print("-" * 70)

    # --------------------------------------------------
    # VALIDATE QWEN OUTPUT
    # --------------------------------------------------

    assert len(
        relevance_result.experience_decisions
    ) == 2

    decisions = {
        decision.experience_index:
        decision.decision
        for decision in (
            relevance_result.experience_decisions
        )
    }

    assert decisions[0] == "RELEVANT"

    assert decisions[1] == "IRRELEVANT"

    # --------------------------------------------------
    # PASS QWEN OUTPUT TO MATCHING SERVICE
    # --------------------------------------------------

    relevance_results = [
        decision.model_dump()
        for decision in (
            relevance_result.experience_decisions
        )
    ]

    matching_result = (
        experience_matching_service.match_experience(
            resume=resume,
            job_description=job_description,
            relevance_results=relevance_results,
        )
    )

    # --------------------------------------------------
    # VERIFY PYTHON MATCHING
    # --------------------------------------------------

    print("\nPYTHON EXPERIENCE MATCHING:\n")

    print(
        "Relevant experience found:",
        matching_result[
            "relevant_experience_found"
        ],
    )

    print(
        "Relevant duration:",
        matching_result[
            "relevant_duration_years"
        ],
        "years",
    )

    print(
        "Minimum satisfied:",
        matching_result[
            "minimum_duration_satisfied"
        ],
    )

    print(
        "Maximum exceeded:",
        matching_result[
            "maximum_duration_exceeded"
        ],
    )

    assert (
        matching_result[
            "relevant_experience_found"
        ]
        is True
    )

    assert (
        matching_result[
            "relevant_duration_years"
        ]
        == 3.0
    )

    assert (
        matching_result[
            "minimum_duration_satisfied"
        ]
        is True
    )

    assert (
        matching_result[
            "maximum_duration_exceeded"
        ]
        is False
    )

    print("\nTEST 1 PASSED")


# ======================================================
# TEST 2
# OVERLAPPING EXPERIENCE
#
# NO QWEN
# PYTHON MATCHING ONLY
# ======================================================

async def test_overlapping_relevant_experience():
    print("\n" + "=" * 70)
    print(
        "TEST 2: OVERLAPPING RELEVANT EXPERIENCE"
    )
    print("=" * 70)

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
        ],
        responsibilities=[
            "Develop banking software",
        ],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2,
                preferred_domains=[
                    "Banking Technology",
                ],
            )
        ],
        tools_and_technologies=[
            "Python",
        ],
    )

    resume = ResumeObject(
        name="Overlap Candidate",
        experience=[
            Experience(
                company="Banking Company A",
                role="Software Engineer",
                start_date="2021-01",
                end_date="2024-01",
                description=(
                    "Developed banking software using Python."
                ),
            ),
            Experience(
                company="Banking Company B",
                role="Consultant",
                start_date="2022-01",
                end_date="2023-01",
                description=(
                    "Worked on banking software systems "
                    "and Python applications."
                ),
            ),
        ],
    )

    # --------------------------------------------------
    # NO QWEN CALL
    #
    # We already know these experiences are relevant.
    # This test is ONLY for duration and overlap logic.
    # --------------------------------------------------

    relevance_results = [
        {
            "experience_index": 0,
            "decision": "RELEVANT",
        },
        {
            "experience_index": 1,
            "decision": "RELEVANT",
        },
    ]

    # --------------------------------------------------
    # PYTHON MATCHING
    # --------------------------------------------------

    result = (
        experience_matching_service.match_experience(
            resume=resume,
            job_description=job_description,
            relevance_results=relevance_results,
        )
    )

    print("\nPYTHON MATCHING RESULT:\n")

    print(
        "Relevant duration:",
        result[
            "relevant_duration_years"
        ],
        "years",
    )

    print(
        "Minimum satisfied:",
        result[
            "minimum_duration_satisfied"
        ],
    )

    # --------------------------------------------------
    # EXPECTATION
    #
    # 2021-01 → 2024-01 = approximately 3 years
    #
    # 2022-01 → 2023-01 is completely inside the first
    # period and therefore must NOT be counted again.
    # --------------------------------------------------

    assert (
        result[
            "relevant_duration_years"
        ]
        < 3.2
    )

    assert (
        result[
            "relevant_duration_years"
        ]
        >= 2
    )

    assert (
        result[
            "minimum_duration_satisfied"
        ]
        is True
    )

    print(
        "\nOverlapping experience was correctly "
        "counted only once."
    )

    print("\nTEST 2 PASSED")


# ======================================================
# TEST 3
# RELEVANT EXPERIENCE WITHOUT DATES
#
# NO QWEN
# PYTHON MATCHING ONLY
# ======================================================

async def test_relevant_experience_without_dates():
    print("\n" + "=" * 70)
    print(
        "TEST 3: RELEVANT EXPERIENCE WITHOUT DATES"
    )
    print("=" * 70)

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
        ],
        responsibilities=[
            "Develop banking software",
        ],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2,
                preferred_domains=[
                    "Banking Technology",
                ],
            )
        ],
        tools_and_technologies=[
            "Python",
        ],
    )

    resume = ResumeObject(
        name="Missing Dates Candidate",
        experience=[
            Experience(
                company="Banking Technology Company",
                role="Software Engineer",
                start_date=None,
                end_date=None,
                description=(
                    "Developed banking software using Python "
                    "and worked on payment processing systems."
                ),
            ),
        ],
    )

    # --------------------------------------------------
    # NO QWEN CALL
    #
    # Relevance is supplied because this test is only
    # checking the Python duration behavior.
    # --------------------------------------------------

    relevance_results = [
        {
            "experience_index": 0,
            "decision": "RELEVANT",
        }
    ]

    # --------------------------------------------------
    # PYTHON MATCHING
    # --------------------------------------------------

    result = (
        experience_matching_service.match_experience(
            resume=resume,
            job_description=job_description,
            relevance_results=relevance_results,
        )
    )

    print("\nPYTHON MATCHING RESULT:\n")

    print(
        "Relevant experience found:",
        result[
            "relevant_experience_found"
        ],
    )

    print(
        "Relevant duration:",
        result[
            "relevant_duration_years"
        ],
        "years",
    )

    experience_result = (
        result["experiences"][0]
    )

    print(
        "Decision:",
        experience_result[
            "decision"
        ],
    )

    print(
        "Duration available:",
        experience_result[
            "duration_available"
        ],
    )

    # --------------------------------------------------
    # RELEVANCE AND DURATION ARE INDEPENDENT
    # --------------------------------------------------

    assert (
        result[
            "relevant_experience_found"
        ]
        is True
    )

    assert (
        result[
            "relevant_duration_years"
        ]
        == 0.0
    )

    assert (
        experience_result[
            "duration_available"
        ]
        is False
    )

    print(
        "\nRelevant experience was preserved even "
        "though its duration could not be calculated."
    )

    print("\nTEST 3 PASSED")


# ======================================================
# TEST 4
# NO EXPERIENCE REQUIREMENT
#
# QWEN SHOULD BE SKIPPED
# ======================================================

async def test_no_experience_requirement():
    print("\n" + "=" * 70)
    print(
        "TEST 4: NO EXPERIENCE REQUIREMENT"
    )
    print("=" * 70)

    job_description = JobDescriptionObject(
        required_skills=[
            "Python",
            "SQL",
        ],
        responsibilities=[
            "Assist with data analysis",
        ],
        experience_requirements=[],
        tools_and_technologies=[
            "Python",
            "SQL",
        ],
    )

    resume = ResumeObject(
        name="Fresher Candidate",
        experience=[],
    )

    # --------------------------------------------------
    # QWEN CALL
    #
    # The service itself must skip Qwen because the JD
    # has no meaningful experience requirement.
    # --------------------------------------------------

    relevance_result = (
        await experience_llm_service.evaluate_experiences(
            job_description=job_description,
            resume=resume,
        )
    )

    assert (
        relevance_result.experience_decisions
        == []
    )

    print(
        "\nQwen correctly skipped."
    )

    # --------------------------------------------------
    # PYTHON MATCHING
    # --------------------------------------------------

    result = (
        experience_matching_service.match_experience(
            resume=resume,
            job_description=job_description,
            relevance_results=[],
        )
    )

    print(
        "Experience requirement present:",
        result[
            "experience_requirement_present"
        ],
    )

    print(
        "Relevant duration:",
        result[
            "relevant_duration_years"
        ],
    )

    print(
        "Minimum satisfied:",
        result[
            "minimum_duration_satisfied"
        ],
    )

    # --------------------------------------------------
    # ASSERTIONS
    # --------------------------------------------------

    assert (
        result[
            "experience_requirement_present"
        ]
        is False
    )

    assert (
        result[
            "relevant_duration_years"
        ]
        == 0.0
    )

    assert (
        result[
            "minimum_duration_satisfied"
        ]
        is True
    )

    print("\nTEST 4 PASSED")


# ======================================================
# MAIN
# ======================================================

async def main():

    # Qwen is used only for relevance detection.
    await test_qwen_relevance_integration()

    # The following tests do NOT call Qwen.
    await test_overlapping_relevant_experience()

    await test_relevant_experience_without_dates()

    # Qwen is called only to verify that it skips
    # a fresher/no-experience JD.
    await test_no_experience_requirement()

    print("\n" + "=" * 70)
    print(
        "ALL EXPERIENCE PIPELINE TESTS PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
