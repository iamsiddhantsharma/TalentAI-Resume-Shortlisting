from app.services.extraction_validator import (
    extraction_validator,
)


def main():

    print("=" * 60)
    print("PHASE 5.6 - PYDANTIC VALIDATION TEST")
    print("=" * 60)

    # ---------------------------------------------
    # Valid resume
    # ---------------------------------------------

    valid_resume = {
        "name": "Siddhant Sharma",
        "email": None,
        "phone": None,
        "location": None,
        "summary": (
            "B.Tech student interested in "
            "backend engineering and AI."
        ),
        "skills": [
            "Python",
            "C++",
            "FastAPI",
            "MongoDB",
        ],
        "education": [
            {
                "degree": "B.Tech",
                "field_of_study": (
                    "Internet of Things Engineering"
                ),
                "institution": None,
                "start_year": None,
                "end_year": None,
                "grade": None,
            }
        ],
        "experience": [],
        "projects": [
            {
                "name": "AI Resume Shortlister",
                "description": (
                    "Resume processing and "
                    "candidate matching system."
                ),
                "technologies": [
                    "Python",
                    "FastAPI",
                ],
            }
        ],
        "certifications": [],
        "achievements": [],
        "interests": [
            "Artificial Intelligence",
            "Backend Development",
        ],
    }

    resume = (
        extraction_validator.validate_resume(
            valid_resume
        )
    )

    print("\n========== VALID RESUME ==========")
    print(resume.model_dump())

    print("\n✓ Resume Pydantic validation passed")

    # ---------------------------------------------
    # Valid JD
    # ---------------------------------------------

    valid_jd = {
        "job_title": "Backend Software Engineer",
        "company": None,
        "location": None,
        "employment_type": None,
        "minimum_experience_years": 1,
        "maximum_experience_years": 3,
        "education_requirements": [
            "Bachelor's degree in Computer Science"
        ],
        "required_skills": [
            "Python",
            "FastAPI",
            "MongoDB",
        ],
        "preferred_skills": [
            "Docker",
            "AWS",
        ],
        "requirements": [],
        "responsibilities": [
            "Build REST APIs",
            "Develop backend services",
        ],
        "qualifications": [],
        "preferred_qualifications": [],
        "benefits": [],
    }

    jd = (
        extraction_validator.validate_job_description(
            valid_jd
        )
    )

    print("\n========== VALID JD ==========")
    print(jd.model_dump())

    print("\n✓ JD Pydantic validation passed")

    # ---------------------------------------------
    # Invalid resume
    # ---------------------------------------------

    invalid_resume = {
        "name": "Siddhant Sharma",
        "skills": "Python, FastAPI",
    }

    try:

        extraction_validator.validate_resume(
            invalid_resume
        )

        raise AssertionError(
            "Invalid resume was incorrectly accepted."
        )

    except ValueError:

        print(
            "\n✓ Invalid resume correctly rejected"
        )

    # ---------------------------------------------
    # Invalid JD
    # ---------------------------------------------

    invalid_jd = {
        "job_title": "Backend Engineer",
        "required_skills": "Python, FastAPI",
    }

    try:

        extraction_validator.validate_job_description(
            invalid_jd
        )

        raise AssertionError(
            "Invalid JD was incorrectly accepted."
        )

    except ValueError:

        print(
            "✓ Invalid JD correctly rejected"
        )

    print("\n" + "=" * 60)
    print("PHASE 5.6 VALIDATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
