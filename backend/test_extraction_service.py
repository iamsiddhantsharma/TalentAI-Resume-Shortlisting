import asyncio

from app.services.extraction_service import (
    extraction_service,
)


async def main():
    print("=" * 60)
    print("PHASE 5.5 - REALISTIC STRUCTURED EXTRACTION TEST")
    print("=" * 60)

    # --------------------------------------------------
    # Realistic resume text
    # --------------------------------------------------

    resume_text = """
    Siddhant Sharma is a B.Tech student specializing in Internet
    of Things Engineering with a strong interest in software
    development, artificial intelligence and backend engineering.
    He has hands-on experience working with Python, C++, FastAPI,
    MongoDB, MySQL, REST APIs, machine learning and natural
    language processing. He has developed an AI Resume Shortlister
    application that processes resumes, extracts useful candidate
    information and performs intelligent candidate matching. The
    project uses Python and FastAPI for backend development and
    includes document parsing and text processing capabilities.

    Siddhant completed his schooling before pursuing his B.Tech
    degree in Internet of Things Engineering. During his academic
    work, he has worked on several software and IoT projects and
    has experience developing applications using Python and C++.
    He has also worked with ESP32 microcontrollers and sensors
    while developing an IoT-based fitness monitoring project.

    He has solved more than 150 programming and data structures
    problems and regularly practices competitive programming.
    His technical interests include artificial intelligence,
    machine learning, backend development, databases and
    distributed systems. He is comfortable working with Git,
    GitHub, Python, FastAPI, MongoDB and MySQL.
    """

    print("\nExtracting realistic resume...")

    resume_result = (
        await extraction_service.extract_resume(
            resume_text
        )
    )

    print("\n========== RESUME JSON ==========")
    print(resume_result)

    # --------------------------------------------------
    # Resume validation
    # --------------------------------------------------

    assert isinstance(
        resume_result,
        dict,
    )

    assert "name" in resume_result
    assert "skills" in resume_result
    assert "education" in resume_result
    assert "experience" in resume_result
    assert "projects" in resume_result

    print("\n✓ Resume extraction completed")
    print("✓ Resume structured JSON received")
    print("✓ Resume structure looks correct")

    # --------------------------------------------------
    # Realistic job description text
    # --------------------------------------------------

    jd_text = """
    We are looking for a Backend Software Engineer to join our
    engineering team and help us build reliable and scalable
    backend applications. The ideal candidate should have strong
    programming skills in Python and practical experience building
    REST APIs using frameworks such as FastAPI or Django. The
    candidate should be comfortable working with relational and
    NoSQL databases including MySQL and MongoDB and should
    understand database design, queries and data modelling.

    The role involves designing and developing backend services,
    creating and maintaining REST APIs, integrating databases,
    writing clean and maintainable Python code, debugging
    production issues and collaborating with frontend and
    engineering teams. The engineer will also participate in
    code reviews and contribute to improving application
    performance and reliability.

    Candidates should have between one and three years of
    software development experience. A bachelor's degree in
    computer science, information technology, software
    engineering or a related technical field is preferred.

    Experience with Docker, Git, GitHub, cloud platforms such as
    AWS and basic knowledge of machine learning or artificial
    intelligence would be an advantage, although these skills
    are not mandatory. Strong problem-solving ability,
    communication skills and the ability to work effectively
    in a team are also expected.
    """

    print("\nExtracting realistic job description...")

    jd_result = (
        await extraction_service.extract_job_description(
            jd_text
        )
    )

    print("\n========== JOB DESCRIPTION JSON ==========")
    print(jd_result)

    # --------------------------------------------------
    # JD validation
    # --------------------------------------------------

    assert isinstance(
        jd_result,
        dict,
    )

    assert "job_title" in jd_result
    assert "minimum_experience_years" in jd_result
    assert "maximum_experience_years" in jd_result
    assert "required_skills" in jd_result
    assert "preferred_skills" in jd_result
    assert "skill_experience_requirements" in jd_result
    assert "responsibilities" in jd_result

    # --------------------------------------------------
    # Verify general experience extraction
    # --------------------------------------------------

    assert (
        jd_result["minimum_experience_years"] == 1
    )

    assert (
        jd_result["maximum_experience_years"] == 3
    )

    # --------------------------------------------------
    # Verify requirements structure
    # --------------------------------------------------

    assert isinstance(
        jd_result["skill_experience_requirements"],
        list,
    )

    for requirement in jd_result[
        "skill_experience_requirements"
    ]:

        assert isinstance(
            requirement,
            dict,
        )

        assert "skill" in requirement
        assert "importance" in requirement
        assert "minimum_years" in requirement
        assert "maximum_years" in requirement

    print("\n✓ JD extraction completed")
    print("✓ JD structured JSON received")
    print("✓ General experience extracted correctly")
    print("✓ Skill experience requirements have correct structure")
    print("✓ JD structure looks correct")

    print("\n" + "=" * 60)
    print("PHASE 5.5 REALISTIC TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
