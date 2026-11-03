from app.schemas.resume_object import (
    ResumeObject,
    Experience,
)

from app.schemas.job_description_object import (
    JobDescriptionObject,
    ExperienceRequirement,
)

from app.services.experience_matching_service import (
    experience_matching_service,
)


def print_separator():
    print("\n" + "-" * 70)


def create_jd(
    minimum_years=None,
    maximum_years=None,
    preferred_domains=None,
):
    return JobDescriptionObject(
        required_skills=[],
        responsibilities=[],
        experience_requirements=(
            [
                ExperienceRequirement(
                    minimum_years=minimum_years,
                    maximum_years=maximum_years,
                    preferred_domains=(
                        preferred_domains or []
                    ),
                )
            ]
            if (
                minimum_years is not None
                or maximum_years is not None
                or preferred_domains
            )
            else []
        ),
        tools_and_technologies=[],
    )


def create_resume(experiences):
    return ResumeObject(
        name="Test Candidate",
        email="test@example.com",
        phone=None,
        location=None,
        summary=None,
        skills=[],
        education=[],
        experience=experiences,
        projects=[],
        certifications=[],
        achievements=[],
        interests=[],
    )


def run_match(
    test_name,
    resume,
    jd,
    relevance_results,
    threshold=0.60,
):
    result = (
        experience_matching_service.match_experience(
            resume=resume,
            job_description=jd,
            relevance_results=relevance_results,
            relevance_threshold=threshold,
        )
    )

    print_separator()
    print(test_name)
    print_separator()

    print(
        "Minimum years:          ",
        result[
            "experience_requirements"
        ]["minimum_years"],
    )

    print(
        "Maximum years:          ",
        result[
            "experience_requirements"
        ]["maximum_years"],
    )

    print(
        "Preferred domains:      ",
        result[
            "experience_requirements"
        ]["preferred_domains"],
    )

    print(
        "Relevant experience:    ",
        result[
            "relevant_experience_found"
        ],
    )

    print(
        "Relevant duration:      ",
        result[
            "relevant_duration_years"
        ],
        "years",
    )

    print(
        "Minimum satisfied:      ",
        result[
            "minimum_duration_satisfied"
        ],
    )

    print(
        "Maximum exceeded:       ",
        result[
            "maximum_duration_exceeded"
        ],
    )

    print("\nExperience details:")

    for experience in result[
        "experiences"
    ]:

        print(
            f"  [{experience['experience_index']}] "
            f"{experience['role']} "
            f"@ {experience['company']}"
        )

        print(
            f"      Relevance: "
            f"{experience['relevance_score']}"
        )

        print(
            f"      Relevant:  "
            f"{experience['relevant']}"
        )

        print(
            f"      Duration:  "
            f"{experience['duration_years']} years"
        )

    return result


def main():

    print("=" * 70)
    print("EXPERIENCE MATCHING ENGINE TEST")
    print("=" * 70)

    # ========================================================
    # CASE 1
    # Relevant experience satisfies minimum duration
    # ========================================================

    resume = create_resume(
        [
            Experience(
                company="Tech Company",
                role="Software Engineer",
                start_date="2020-01",
                end_date="2023-01",
                description=(
                    "Developed backend services "
                    "and APIs."
                ),
            )
        ]
    )

    jd = create_jd(
        minimum_years=2,
        maximum_years=5,
        preferred_domains=[
            "Technology"
        ],
    )

    result = run_match(
        "CASE 1 — Relevant experience satisfies minimum",
        resume,
        jd,
        [
            {
                "experience_index": 0,
                "relevance_score": 0.90,
            }
        ],
    )

    assert result[
        "relevant_experience_found"
    ] is True

    assert result[
        "minimum_duration_satisfied"
    ] is True

    # ========================================================
    # CASE 2
    # Relevant experience but duration insufficient
    # Candidate must NOT be rejected
    # ========================================================

    resume = create_resume(
        [
            Experience(
                company="Startup",
                role="Data Scientist",
                start_date="2023-01",
                end_date="2024-07",
                description=(
                    "Built machine learning models "
                    "for customer prediction."
                ),
            )
        ]
    )

    jd = create_jd(
        minimum_years=2,
        maximum_years=5,
        preferred_domains=[
            "Technology"
        ],
    )

    result = run_match(
        "CASE 2 — Relevant but duration insufficient",
        resume,
        jd,
        [
            {
                "experience_index": 0,
                "relevance_score": 0.92,
            }
        ],
    )

    assert result[
        "relevant_experience_found"
    ] is True

    assert result[
        "minimum_duration_satisfied"
    ] is False

    # Candidate remains relevant.
    assert result[
        "experiences"
    ][0]["relevant"] is True

    # ========================================================
    # CASE 3
    # Irrelevant experience must not count
    # ========================================================

    resume = create_resume(
        [
            Experience(
                company="Design Studio",
                role="Graphic Designer",
                start_date="2018-01",
                end_date="2023-01",
                description=(
                    "Created branding and visual "
                    "design materials."
                ),
            )
        ]
    )

    jd = create_jd(
        minimum_years=2,
        maximum_years=5,
        preferred_domains=[
            "Technology"
        ],
    )

    result = run_match(
        "CASE 3 — Irrelevant experience does not count",
        resume,
        jd,
        [
            {
                "experience_index": 0,
                "relevance_score": 0.25,
            }
        ],
    )

    assert result[
        "relevant_experience_found"
    ] is False

    assert result[
        "relevant_duration_years"
    ] == 0.0

    assert result[
        "experiences"
    ][0]["relevant"] is False

    # ========================================================
    # CASE 4
    # Overlapping relevant experience must not double count
    # ========================================================

    resume = create_resume(
        [
            Experience(
                company="Company A",
                role="Software Engineer",
                start_date="2020-01",
                end_date="2023-01",
                description=(
                    "Developed software systems."
                ),
            ),
            Experience(
                company="Company B",
                role="Consultant",
                start_date="2021-01",
                end_date="2022-01",
                description=(
                    "Provided software engineering "
                    "consulting."
                ),
            ),
        ]
    )

    jd = create_jd(
        minimum_years=2,
        maximum_years=5,
        preferred_domains=[
            "Technology"
        ],
    )

    result = run_match(
        "CASE 4 — Overlapping experience is not double counted",
        resume,
        jd,
        [
            {
                "experience_index": 0,
                "relevance_score": 0.90,
            },
            {
                "experience_index": 1,
                "relevance_score": 0.85,
            },
        ],
    )

    assert result[
        "relevant_experience_found"
    ] is True

    # Should be approximately 3 years,
    # NOT approximately 4 years.
    assert (
        2.9
        <= result[
            "relevant_duration_years"
        ]
        <= 3.1
    )

    # ========================================================
    # CASE 5
    # Ongoing/current experience
    # ========================================================

    resume = create_resume(
        [
            Experience(
                company="Current Company",
                role="ML Engineer",
                start_date="2023-01",
                end_date="Present",
                description=(
                    "Developing machine learning "
                    "systems."
                ),
            )
        ]
    )

    jd = create_jd(
        minimum_years=1,
        maximum_years=5,
        preferred_domains=[
            "Technology"
        ],
    )

    result = run_match(
        "CASE 5 — Ongoing experience",
        resume,
        jd,
        [
            {
                "experience_index": 0,
                "relevance_score": 0.88,
            }
        ],
    )

    assert result[
        "relevant_experience_found"
    ] is True

    assert (
        result[
            "relevant_duration_years"
        ]
        > 0
    )

    # ========================================================
    # CASE 6
    # Relevant experience but missing dates
    #
    # Relevance remains valid.
    # Duration simply cannot be calculated.
    # ========================================================

    resume = create_resume(
        [
            Experience(
                company="Technology Company",
                role="Backend Developer",
                start_date=None,
                end_date=None,
                description=(
                    "Built REST APIs and backend "
                    "services."
                ),
            )
        ]
    )

    jd = create_jd(
        minimum_years=2,
        maximum_years=5,
        preferred_domains=[
            "Technology"
        ],
    )

    result = run_match(
        "CASE 6 — Relevant experience with missing dates",
        resume,
        jd,
        [
            {
                "experience_index": 0,
                "relevance_score": 0.91,
            }
        ],
    )

    assert result[
        "experiences"
    ][0]["relevant"] is True

    # Under Phase 3 decoupled architecture:
    # Relevant work is confirmed qualitatively (True), but has no duration credit (0.0).
    assert result[
        "relevant_experience_found"
    ] is True

    assert result[
        "relevant_duration_years"
    ] == 0.0

    # ========================================================
    # CASE 7
    # No experience requirement in JD
    # ========================================================

    resume = create_resume(
        [
            Experience(
                company="Company",
                role="Software Engineer",
                start_date="2020-01",
                end_date="2023-01",
                description=(
                    "Built backend systems."
                ),
            )
        ]
    )

    jd = create_jd()

    result = run_match(
        "CASE 7 — JD has no experience requirement",
        resume,
        jd,
        [
            {
                "experience_index": 0,
                "relevance_score": 0.90,
            }
        ],
    )

    assert result[
        "experience_requirements"
    ]["minimum_years"] is None

    assert result[
        "experience_requirements"
    ]["maximum_years"] is None

    assert result[
        "relevant_experience_found"
    ] is True

    # ========================================================
    # FINAL
    # ========================================================

    print("\n" + "=" * 70)
    print("ALL EXPERIENCE MATCHING TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
