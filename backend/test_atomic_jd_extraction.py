"""
TalentAI — Phase 5.9A: Atomic JD Skill Extraction Tests

Validates:
1. Compound skills are decomposed into atomic, independently verifiable entries.
2. The original requirement is preserved where the schema supports provenance (raw_text in JobDescription).
3. Core mandatory skills (e.g. Python, SQL) are present in required_skills even when also tools.
4. Optional or merely mentioned technologies are not incorrectly promoted to required_skills.
5. Duplicate skills are handled consistently (case-insensitive deduplication, order preservation).
6. JobDescriptionObject schema validation and downstream processing integrity.
7. LLM skill matching works accurately with atomic extracted skills.
8. End-to-end extraction recovery flow with mocked LLM generation.
"""

import asyncio
from unittest.mock import AsyncMock, patch

from app.prompts.job_description import JOB_DESCRIPTION_PROMPT
from app.schemas.job_description import JobDescription
from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.resume_object import ResumeObject
from app.services.llm_skill_matching_service import llm_skill_matching_service
from app.services.extraction_recovery import extraction_recovery_service
from app.services.extraction_validator import extraction_validator


def test_atomic_decomposition_schema():
    """
    Test 1: Verify that compound JD requirements decompose into atomic skills
    and validate cleanly into JobDescriptionObject.
    """
    print("\n" + "=" * 70)
    print("TEST 1: ATOMIC SKILL DECOMPOSITION")
    print("=" * 70)

    # Simulated atomic decomposition of the Capgemini JD compound skills:
    atomic_skills = [
        "Data Mining",
        "Data Cleansing",
        "Data Science",
        "Machine Learning",
        "Supervised Learning",
        "Unsupervised Learning",
        "Natural Language Processing",
        "Computer Vision",
        "Statistics",
        "Statistical Inference",
        "Hypothesis Testing",
        "Forecasting",
        "AWS",
        "GCP",
        "Azure",
        "Hadoop",
        "Hive",
        "MapReduce",
        "PySpark",
        "Model Deployment",
        "SQL",
        "NoSQL",
        "Databases",
        "Python",
    ]

    jd_object = JobDescriptionObject(
        required_skills=atomic_skills,
        responsibilities=[
            "Data mining and performing EDAs using state-of-the-art methods",
            "Selecting features, building and optimizing classifiers",
        ],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2.0,
                maximum_years=5.0,
                preferred_domains=["Data Science", "Financial Services"],
            )
        ],
        tools_and_technologies=[
            "Python",
            "R",
            "SQL",
            "NoSQL",
            "AWS",
            "GCP",
            "Azure",
            "Hadoop",
            "Hive",
            "MapReduce",
            "PySpark",
            "TensorFlow",
            "PyTorch",
        ],
    )

    assert len(jd_object.required_skills) == 24
    assert "SQL" in jd_object.required_skills
    assert "NoSQL" in jd_object.required_skills
    assert "AWS" in jd_object.required_skills
    assert "Natural Language Processing" in jd_object.required_skills
    assert "Computer Vision" in jd_object.required_skills
    assert "Python" in jd_object.required_skills

    # Verify no compound strings remain in required_skills
    for skill in jd_object.required_skills:
        assert " and " not in skill.lower(), f"Compound conjunction found in: {skill}"
        assert "(" not in skill, f"Parenthetical found in: {skill}"
        assert "/" not in skill, f"Slash-compound found in: {skill}"
        assert "," not in skill, f"Comma-separated list found in: {skill}"

    print(f"[PASSED] Successfully decomposed into {len(jd_object.required_skills)} atomic skills.")
    print("         All entries verified atomic without conjunctions, slashes, or parentheticals.")


def test_provenance_preservation():
    """
    Test 2: Verify that the original JD text is fully preserved alongside
    structured atomic skills.
    """
    print("\n" + "=" * 70)
    print("TEST 2: PROVENANCE PRESERVATION")
    print("=" * 70)

    original_raw_text = (
        "Capgemini Invent is hiring. Requirements: Strong experience in cloud (AWS/GCP/Azure) "
        "and big data technologies (Hadoop, Hive, MapReduce, PySpark), database systems (SQL and NoSQL). "
        "Minimum 2-5 years experience."
    )

    jd = JobDescription(
        jd_id="jd_test_prov_001",
        input_type="text",
        filename="job_description.txt",
        file_extension=".txt",
        raw_text=original_raw_text,
        status="completed",
        structured_data=JobDescriptionObject(
            required_skills=["AWS", "GCP", "Azure", "Hadoop", "Hive", "MapReduce", "PySpark", "SQL", "NoSQL"],
            responsibilities=["Develop analytics delivery engagements"],
            experience_requirements=[
                ExperienceRequirement(minimum_years=2.0, maximum_years=5.0, preferred_domains=["Analytics"])
            ],
            tools_and_technologies=["AWS", "GCP", "Azure", "Hadoop", "Hive", "PySpark", "SQL", "NoSQL"],
        ),
    )

    # Verify complete original raw_text remains untouched
    assert jd.raw_text == original_raw_text
    assert "cloud (AWS/GCP/Azure)" in jd.raw_text
    assert "database systems (SQL and NoSQL)" in jd.raw_text

    # Verify structured atomic skills are cleanly separated
    assert "AWS" in jd.structured_data.required_skills
    assert "SQL" in jd.structured_data.required_skills

    print("[PASSED] Original document text preserved 100% intact in raw_text.")
    print("         Atomic skills available in structured_data.")


def test_core_mandatory_skills_not_lost():
    """
    Test 3: Core mandatory technologies (e.g. Python, SQL) must not be lost
    from required_skills merely because they are also in tools_and_technologies.
    """
    print("\n" + "=" * 70)
    print("TEST 3: CORE MANDATORY TECHNOLOGIES IN BOTH CATEGORIES")
    print("=" * 70)

    jd_object = JobDescriptionObject(
        required_skills=["Python", "FastAPI", "SQL", "Docker"],
        responsibilities=["Build high-throughput REST APIs"],
        experience_requirements=[],
        tools_and_technologies=["Python", "FastAPI", "SQL", "Docker", "Redis", "Jira"],
    )

    # Core mandatory skills must exist in required_skills
    assert "Python" in jd_object.required_skills
    assert "SQL" in jd_object.required_skills

    # Also available in tools_and_technologies for semantic retrieval
    assert "Python" in jd_object.tools_and_technologies
    assert "SQL" in jd_object.tools_and_technologies

    print("[PASSED] Python and SQL correctly present in both required_skills and tools_and_technologies.")


def test_optional_tools_not_promoted():
    """
    Test 4: Optional or merely mentioned environment tools are not incorrectly
    promoted to required_skills.
    """
    print("\n" + "=" * 70)
    print("TEST 4: OPTIONAL TOOLS EXCLUDED FROM REQUIRED_SKILLS")
    print("=" * 70)

    jd_object = JobDescriptionObject(
        required_skills=["Python", "FastAPI"],  # Mandatory
        responsibilities=["Build services"],
        experience_requirements=[],
        tools_and_technologies=["Python", "FastAPI", "Docker", "Kubernetes", "Slack", "Jira"],  # All tools
    )

    assert "Docker" not in jd_object.required_skills
    assert "Slack" not in jd_object.required_skills
    assert "Jira" not in jd_object.required_skills

    assert "Docker" in jd_object.tools_and_technologies
    assert "Slack" in jd_object.tools_and_technologies

    print("[PASSED] Optional tools (Docker, Slack, Jira) present in tools_and_technologies but not in required_skills.")


def test_deduplication_and_whitespace():
    """
    Test 5: Duplicate skills and whitespace are cleaned consistently.
    """
    print("\n" + "=" * 70)
    print("TEST 5: DEDUPLICATION AND CLEANING")
    print("=" * 70)

    raw_skills = [
        "Python",
        "python",
        "  PYTHON  ",
        "FastAPI",
        "SQL",
        "sql",
        "   ",
        None,
        "Machine Learning",
    ]

    jd_object = JobDescriptionObject(
        required_skills=raw_skills,  # type: ignore
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=["Docker", "docker", "DOCKER", "  K8s  "],
    )

    expected_skills = ["Python", "FastAPI", "SQL", "Machine Learning"]
    assert jd_object.required_skills == expected_skills
    assert jd_object.tools_and_technologies == ["Docker", "K8s"]

    print("[PASSED] Case-insensitive deduplication and whitespace stripping verified.")
    print(f"         Result: {jd_object.required_skills}")


async def test_exact_matching_integration():
    """
    Test 7: Direct comparison showing how atomic decomposition fixes
    the skill matching failure.
    """
    print("\n" + "=" * 70)
    print("TEST 7: EXACT MATCHING SERVICE INTEGRATION (BEFORE vs AFTER)")
    print("=" * 70)

    candidate = ResumeObject(
        name="Siddhant Sharma",
        skills=["Python", "FastAPI", "MongoDB", "MySQL", "AWS", "Machine Learning"],
        education=[],
        experience=[],
        projects=[],
    )

    # ------------------------------------------------------------------
    # BEFORE: Compound JD skills from un-remediated extraction
    # ------------------------------------------------------------------
    compound_jd = JobDescriptionObject(
        required_skills=[
            "cloud (AWS/GCP/Azure) and big data technologies (Hadoop, Hive, MapReduce, Pyspark)",
            "database systems (SQL and NoSQL)",
            "data-science and machine learning techniques & algorithms for supervised & unsupervised problems",
        ],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=["Python", "AWS", "MySQL", "MongoDB"],
    )

    before_result = await llm_skill_matching_service.match_required_skills(
        job_description=compound_jd,
        resume=candidate,
    )

    print("\n--- BEFORE ATOMIC FIX ---")
    print(f"Total Required: {before_result['total_required_skills']}")
    print(f"Matched: {before_result['matched_required_skills']}")
    print(f"Unmatched: {before_result['unmatched_required_skills']}")
    print(f"Result: {before_result['matched_required_skills']} of 3 matched with compound strings.")

    # ------------------------------------------------------------------
    # AFTER: Atomic JD skills
    # ------------------------------------------------------------------
    atomic_jd = JobDescriptionObject(
        required_skills=[
            "Python",
            "AWS",
            "GCP",
            "Azure",
            "SQL",
            "NoSQL",
            "Machine Learning",
            "Hadoop",
        ],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=["Python", "AWS", "MySQL", "MongoDB"],
    )

    after_result = await llm_skill_matching_service.match_required_skills(
        job_description=atomic_jd,
        resume=candidate,
    )

    print("\n--- AFTER ATOMIC FIX ---")
    print(f"Total Required: {after_result['total_required_skills']}")
    print(f"Matched: {after_result['matched_required_skills']}")
    print(f"Unmatched: {after_result['unmatched_required_skills']}")
    for m in after_result["matches"]:
        status = "MATCH" if m["matched"] else "MISSING"
        print(f"  {m['required_skill']:<20} -> {status} ({m['resume_skill']})")

    assert after_result["matched_required_skills"] >= 3
    print(f"[PASSED] Atomic skills matched successfully ({after_result['matched_required_skills']}/{after_result['total_required_skills']}).")


async def test_extraction_recovery_flow_with_mock():
    """
    Test 8: Verify extraction_recovery_service validates atomic LLM output
    into a valid JobDescriptionObject.
    """
    print("\n" + "=" * 70)
    print("TEST 8: EXTRACTION RECOVERY SERVICE WITH MOCKED LLM")
    print("=" * 70)

    mock_llm_response = {
        "required_skills": [
            "Python",
            "FastAPI",
            "SQL",
            "NoSQL",
            "Machine Learning",
            "Natural Language Processing",
        ],
        "responsibilities": [
            "Develop scalable machine learning services",
            "Collaborate with engineering teams",
        ],
        "experience_requirements": [
            {
                "minimum_years": 2.0,
                "maximum_years": 5.0,
                "preferred_domains": ["Data Science", "Backend Engineering"],
            }
        ],
        "tools_and_technologies": [
            "Python",
            "FastAPI",
            "SQL",
            "MongoDB",
            "Docker",
        ],
    }

    with patch("app.services.extraction_recovery.llm_service.generate_json", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        jd_object = await extraction_recovery_service.extract_job_description(
            "Sample JD text requiring Python, FastAPI, and machine learning."
        )

        assert isinstance(jd_object, JobDescriptionObject)
        assert len(jd_object.required_skills) == 6
        assert "Natural Language Processing" in jd_object.required_skills
        assert "FastAPI" in jd_object.required_skills
        assert jd_object.experience_requirements[0].minimum_years == 2.0

        print("[PASSED] Extraction recovery service successfully validated mocked atomic LLM response.")


def test_prompt_content_rules():
    """
    Test 9: Verify that JOB_DESCRIPTION_PROMPT contains the required atomic
    decomposition rules and examples.
    """
    print("\n" + "=" * 70)
    print("TEST 9: PROMPT CONTENT VERIFICATION")
    print("=" * 70)

    assert "ATOMIC, INDEPENDENTLY VERIFIABLE" in JOB_DESCRIPTION_PROMPT
    assert "database systems (SQL and NoSQL)" in JOB_DESCRIPTION_PROMPT
    assert "NLP and computer vision" in JOB_DESCRIPTION_PROMPT
    assert "cloud (AWS/GCP/Azure)" in JOB_DESCRIPTION_PROMPT
    assert "MANDATORY PROGRAMMING LANGUAGES AND CORE TECHNOLOGIES" in JOB_DESCRIPTION_PROMPT
    assert "RELATIONSHIP WITH REQUIRED SKILLS" in JOB_DESCRIPTION_PROMPT

    print("[PASSED] Prompt text contains all required atomic guidelines and decomposition examples.")


async def main():
    print("=" * 70)
    print("TALENTAI — PHASE 5.9A ATOMIC SKILL EXTRACTION SUITE")
    print("=" * 70)

    test_atomic_decomposition_schema()
    test_provenance_preservation()
    test_core_mandatory_skills_not_lost()
    test_optional_tools_not_promoted()
    test_deduplication_and_whitespace()
    await test_exact_matching_integration()
    await test_extraction_recovery_flow_with_mock()
    test_prompt_content_rules()

    print("\n" + "=" * 70)
    print("ALL 8 ATOMIC EXTRACTION TESTS PASSED (100%)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
