from app.schemas.resume_object import ResumeObject
from app.schemas.job_description_object import (
    JobDescriptionObject,
    ExperienceRequirement,
)
from app.services.experience_relevance_service import (
    experience_relevance_service,
)


def main():

    job_description = JobDescriptionObject(
        required_skills=[],
        responsibilities=[],
        tools_and_technologies=[],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2,
                preferred_domains=[
                    "Financial Services",
                    "Technology",
                    "Telecom",
                ],
            )
        ],
    )

    resume = ResumeObject(
        name="Test Candidate",
        experience=[
            {
                "company": "Banking Platform",
                "role": "Software Engineer",
                "description": (
                    "Developed payment processing systems "
                    "and banking APIs."
                ),
                "start_date": "2021-01",
                "end_date": "2024-01",
            },
            {
                "company": "Design Studio",
                "role": "Graphic Designer",
                "description": (
                    "Created branding and visual "
                    "design materials."
                ),
                "start_date": "2022-01",
                "end_date": "2023-01",
            },
            {
                "company": "Telecom Company",
                "role": "Data Analyst",
                "description": (
                    "Analyzed customer usage and "
                    "network metrics."
                ),
                "start_date": "2021-01",
                "end_date": "2024-01",
            },
            {
                "company": "ABC Company",
                "role": "Analyst",
                "description": "",
                "start_date": None,
                "end_date": None,
            },
        ],
    )

    results = (
        experience_relevance_service.match_experience_relevance(
            resume,
            job_description,
        )
    )

    print("\n" + "=" * 80)
    print("EXPERIENCE RELEVANCE FEATURE TEST")
    print("=" * 80)

    for result in results:

        print(
            f"\nExperience #{result['experience_index']}"
        )

        print(
            f"Text: {result['experience_text']}"
        )

        print(
            f"Status: {result['status']}"
        )

        print(
            "Information sufficiency:",
            result["information_sufficiency"],
        )

        if result["domain_matches"]:

            print("\nDomain similarities:")

            for match in result["domain_matches"]:
                print(
                    f"  {match['domain']}: "
                    f"{match['similarity']}"
                )

            print(
                f"\nTop-1 domain: "
                f"{result['top1_domain']}"
            )

            print(
                f"Top-1 score: "
                f"{result['top1_score']}"
            )

            print(
                f"Top-2 domain: "
                f"{result['top2_domain']}"
            )

            print(
                f"Top-2 score: "
                f"{result['top2_score']}"
            )

            print(
                f"Margin: "
                f"{result['margin']}"
            )

        print("-" * 80)


if __name__ == "__main__":
    main()
