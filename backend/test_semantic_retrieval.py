import asyncio
from math import sqrt
from unittest.mock import AsyncMock, patch

from app.schemas.job_description import JobDescription
from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.processing_result import ProcessingResult
from app.schemas.resume_object import (
    Experience,
    Project,
    ResumeObject,
)
from app.services.llm_skill_matching_service import (
    llm_skill_matching_service,
)
from app.services.hybrid_matching_service import (
    hybrid_matching_service,
)
from app.services.semantic_retrieval_service import (
    semantic_retrieval_service,
)


def make_vector(
    similarity: float,
    dim: int = 1024,
) -> list[float]:
    """
    Construct a deterministic unit-normalized vector whose cosine similarity
    with the base vector [1.0, 0.0, ...] is exactly equal to `similarity`.
    """
    clamped = max(-1.0, min(1.0, similarity))
    y = sqrt(max(0.0, 1.0 - clamped * clamped))
    vec = [0.0] * dim
    vec[0] = clamped
    vec[1] = y
    return vec


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


# ==============================================================================
# TEST A: RESPONSIBILITIES
# ==============================================================================


def test_a_responsibilities():
    print("\n" + "=" * 70)
    print("TEST A: RESPONSIBILITIES RETRIEVAL")
    print("=" * 70)

    jd_evidence = {
        "section": "responsibilities",
        "item_index": 0,
        "text": "Responsibility: Build scalable payment systems",
        "embedding": make_vector(1.0),
    }

    resume_embeddings = [
        {
            "section": "skills",
            "item_index": 0,
            "text": "Skill: Payment Architecture",
            "embedding": make_vector(1.0),  # highest similarity
        },
        {
            "section": "education",
            "item_index": 0,
            "text": "Degree: Master in Computer Science",
            "embedding": make_vector(0.95),
        },
        {
            "section": "certifications",
            "item_index": 0,
            "text": "Certification: AWS Solutions Architect",
            "embedding": make_vector(0.92),
        },
        {
            "section": "projects",
            "item_index": 0,
            "text": "Project: Real-time Payment Engine",
            "embedding": make_vector(0.85),
        },
        {
            "section": "experience",
            "item_index": 0,
            "text": "Role: Staff Engineer | Work: Built payment microservices",
            "embedding": make_vector(0.75),
        },
    ]

    matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=resume_embeddings,
        top_k=5,
    )

    # Must only match projects and experience
    assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"

    sections = [m["resume_section"] for m in matches]
    assert sections == ["projects", "experience"], (
        f"Expected ['projects', 'experience'], got {sections}"
    )

    # Must NEVER contain skills, education, or certifications
    disallowed = {"skills", "education", "certifications"}
    for m in matches:
        assert m["resume_section"] not in disallowed, (
            f"Disallowed section found: {m['resume_section']}"
        )

    # Must be sorted descending
    assert matches[0]["similarity"] >= matches[1]["similarity"]
    assert abs(matches[0]["similarity"] - 0.85) < 1e-4
    assert abs(matches[1]["similarity"] - 0.75) < 1e-4

    print_status(
        "Responsibilities only retrieves projects and experience (never skills/education/certs)",
        True,
    )


# ==============================================================================
# TEST B: TOOLS AND TECHNOLOGIES
# ==============================================================================


def test_b_tools_and_technologies():
    print("\n" + "=" * 70)
    print("TEST B: TOOLS AND TECHNOLOGIES RETRIEVAL")
    print("=" * 70)

    jd_evidence = {
        "section": "tools_and_technologies",
        "item_index": 0,
        "text": "Tool or technology: Python",
        "embedding": make_vector(1.0),
    }

    # Setup resume evidence where skills and experience have HIGHER similarity than project
    resume_embeddings = [
        {
            "section": "skills",
            "item_index": 0,
            "text": "Skill: Python",
            "embedding": make_vector(1.0),  # Similarity 1.0 (highest)
        },
        {
            "section": "experience",
            "item_index": 0,
            "text": "Role: Python Developer | Work: Core Python development",
            "embedding": make_vector(0.95),  # Similarity 0.95 (very high)
        },
        {
            "section": "projects",
            "item_index": 0,
            "text": "Project: Async Web Crawler in Python",
            "embedding": make_vector(0.75),  # Similarity 0.75 (qualifies above 0.65 threshold)
        },
    ]

    matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=resume_embeddings,
        top_k=5,
    )

    # MUST ONLY match projects, despite skills and experience having higher similarities
    assert len(matches) == 1, f"Expected 1 match, got {len(matches)}"
    assert matches[0]["resume_section"] == "projects", (
        f"Expected section 'projects', got '{matches[0]['resume_section']}'"
    )
    assert matches[0]["resume_text"] == "Project: Async Web Crawler in Python"
    assert abs(matches[0]["similarity"] - 0.75) < 1e-4

    # Assert neither skills nor experience entered the result
    for m in matches:
        assert m["resume_section"] not in {"skills", "experience"}, (
            f"Disallowed section in tools retrieval: {m['resume_section']}"
        )

    print_status(
        "Tools and technologies retrieves projects only (never skills or experience)",
        True,
    )


# ==============================================================================
# TEST C: REQUIRED SKILLS EXCLUDED FROM SEMANTIC RETRIEVAL
# ==============================================================================


async def test_c_required_skills():
    print("\n" + "=" * 70)
    print("TEST C: REQUIRED SKILLS EXCLUSION")
    print("=" * 70)

    # 1. Allowed resume sections for required_skills must be empty
    allowed = semantic_retrieval_service.get_allowed_resume_sections(
        "required_skills"
    )
    assert allowed == set(), (
        f"Expected empty allowed sections for required_skills, got {allowed}"
    )

    # 2. Retrieval returns empty when queried with required_skills
    jd_evidence = {
        "section": "required_skills",
        "item_index": 0,
        "text": "Required skill: Machine Learning",
        "embedding": make_vector(1.0),
    }

    resume_embeddings = [
        {
            "section": "skills",
            "item_index": 0,
            "text": "Skill: Machine Learning",
            "embedding": make_vector(1.0),
        },
        {
            "section": "projects",
            "item_index": 0,
            "text": "Project: ML Pipeline",
            "embedding": make_vector(0.9),
        },
    ]

    matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=resume_embeddings,
        top_k=5,
    )
    assert matches == [], (
        f"Required skills must return empty semantic matches, got {matches}"
    )

    all_matches = semantic_retrieval_service.retrieve_for_all_jd_evidence(
        jd_embeddings=[jd_evidence],
        resume_embeddings=resume_embeddings,
        top_k=5,
    )
    assert len(all_matches) == 1
    assert all_matches[0]["matches"] == []

    # 3. LLM skill matching remains responsible for required skills
    jd_obj = JobDescriptionObject(
        required_skills=["Machine Learning"],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )
    res_obj = ResumeObject(
        skills=["Machine-Learning"],
        projects=[],
        experience=[],
    )
    llm_res = await llm_skill_matching_service.match_required_skills(
        job_description=jd_obj,
        resume=res_obj,
    )
    assert llm_res["matched_required_skills"] == 1
    assert llm_res["matches"][0]["matched"] is True

    print_status(
        "Required skills excluded from semantic retrieval; handled by LLM skill matching",
        True,
    )


# ==============================================================================
# TEST D: EXPERIENCE REQUIREMENTS EXCLUDED FROM SEMANTIC RETRIEVAL
# ==============================================================================


def test_d_experience_requirements():
    print("\n" + "=" * 70)
    print("TEST D: EXPERIENCE REQUIREMENTS EXCLUSION")
    print("=" * 70)

    # 1. Allowed resume sections for experience_requirements must be empty
    allowed = semantic_retrieval_service.get_allowed_resume_sections(
        "experience_requirements"
    )
    assert allowed == set(), (
        f"Expected empty allowed sections for experience_requirements, got {allowed}"
    )

    # 2. Retrieval returns empty when queried with experience_requirements
    jd_evidence = {
        "section": "experience_requirements",
        "item_index": 0,
        "text": "Minimum experience: 3 years | Preferred domains: Banking",
        "embedding": make_vector(1.0),
    }

    resume_embeddings = [
        {
            "section": "experience",
            "item_index": 0,
            "text": "Role: Banking Software Engineer",
            "embedding": make_vector(0.9),
        }
    ]

    matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=resume_embeddings,
        top_k=5,
    )
    assert matches == [], (
        f"Experience requirements must return empty semantic matches, got {matches}"
    )

    print_status(
        "Experience requirements excluded from semantic retrieval",
        True,
    )


# ==============================================================================
# TEST E: PROVENANCE AND TOP-K
# ==============================================================================


def test_e_provenance_and_top_k():
    print("\n" + "=" * 70)
    print("TEST E: PROVENANCE AND TOP-K VERIFICATION")
    print("=" * 70)

    jd_evidence = {
        "section": "tools_and_technologies",
        "item_index": 2,
        "text": "Tool or technology: Docker",
        "embedding": make_vector(1.0),
    }

    # 7 candidate project evidence units with known descending similarities
    sim_values = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65]
    resume_embeddings = [
        {
            "section": "projects",
            "item_index": i,
            "text": f"Project #{i} with Docker containerization",
            "embedding": make_vector(sim),
        }
        for i, sim in enumerate(sim_values)
    ]

    matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=resume_embeddings,
        top_k=5,
    )

    # Assert top_k=5 is respected
    assert len(matches) == 5, f"Expected 5 matches, got {len(matches)}"

    # Assert sorted descending
    actual_sims = [m["similarity"] for m in matches]
    expected_sims = sim_values[:5]
    for actual, expected in zip(actual_sims, expected_sims):
        assert abs(actual - expected) < 1e-4

    # Assert all provenance fields exist
    expected_fields = {
        "jd_section",
        "jd_item_index",
        "jd_text",
        "resume_section",
        "resume_item_index",
        "resume_text",
        "similarity",
    }
    for m in matches:
        assert expected_fields.issubset(m.keys()), (
            f"Missing provenance field in: {m}"
        )
        assert m["jd_section"] == "tools_and_technologies"
        assert m["jd_item_index"] == 2
        assert m["jd_text"] == "Tool or technology: Docker"
        assert m["resume_section"] == "projects"

    print_status(
        "Full provenance preserved, similarities sorted descending, top-k=5 respected",
        True,
    )


# ==============================================================================
# TEST F: EMPTY AND UNKNOWN SECTIONS
# ==============================================================================


def test_f_empty_and_unknown_sections():
    print("\n" + "=" * 70)
    print("TEST F: EMPTY AND UNKNOWN SECTIONS HANDLING")
    print("=" * 70)

    valid_evidence = {
        "section": "responsibilities",
        "item_index": 0,
        "text": "Responsibility: System design",
        "embedding": make_vector(1.0),
    }

    # 1. Empty JD evidence list returns empty
    res1 = semantic_retrieval_service.retrieve_for_all_jd_evidence(
        jd_embeddings=[],
        resume_embeddings=[{"section": "projects", "embedding": make_vector(1.0)}],
    )
    assert res1 == []

    # 2. Empty resume embeddings returns empty
    res2 = semantic_retrieval_service.retrieve_for_all_jd_evidence(
        jd_embeddings=[valid_evidence],
        resume_embeddings=[],
    )
    assert res2 == []

    # 3. Unknown JD section returns empty and does NOT perform unrestricted search
    unknown_evidence = {
        "section": "unrecognized_section_123",
        "item_index": 0,
        "text": "Unknown requirement",
        "embedding": make_vector(1.0),
    }

    res_unknown = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=unknown_evidence,
        resume_embeddings=[
            {
                "section": "projects",
                "item_index": 0,
                "text": "Project A",
                "embedding": make_vector(1.0),
            },
            {
                "section": "skills",
                "item_index": 0,
                "text": "Skill A",
                "embedding": make_vector(1.0),
            },
        ],
    )
    assert res_unknown == [], f"Unknown JD section must return [], got {res_unknown}"

    # 4. Resume evidence with missing/None section is safely skipped
    res_missing_section = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=valid_evidence,
        resume_embeddings=[
            {
                "section": None,
                "item_index": 0,
                "text": "Corrupted evidence",
                "embedding": make_vector(1.0),
            },
            {
                "section": "projects",
                "item_index": 1,
                "text": "Valid Project",
                "embedding": make_vector(0.8),
            },
        ],
    )
    assert len(res_missing_section) == 1
    assert res_missing_section[0]["resume_section"] == "projects"

    print_status(
        "Empty evidence and unknown sections handled safely without unrestricted search",
        True,
    )


# ==============================================================================
# TEST G: HYBRID ORCHESTRATION
# ==============================================================================


async def test_g_hybrid_orchestration():
    print("\n" + "=" * 70)
    print("TEST G: HYBRID ORCHESTRATION ISOLATION & STRUCTURE")
    print("=" * 70)

    # Synthetic JD with all sections
    synthetic_jd_dict = {
        "_id": "mock_jd_001",
        "jd_id": "mock_jd_001",
        "input_type": "text",
        "raw_text": "Python developer role",
        "status": "completed",
        "structured_data": {
            "required_skills": ["Python", "FastAPI"],
            "responsibilities": ["Build microservices"],
            "experience_requirements": [
                {
                    "minimum_years": 2.0,
                    "maximum_years": 5.0,
                    "preferred_domains": ["Fintech"],
                }
            ],
            "tools_and_technologies": ["Docker"],
        },
    }

    # Synthetic JD embeddings for ALL 4 sections
    synthetic_jd_embeddings = {
        "_id": "active_jd",
        "jd_id": "mock_jd_001",
        "embeddings": [
            {
                "section": "required_skills",
                "item_index": 0,
                "text": "Required skill: Python",
                "embedding": make_vector(1.0),
            },
            {
                "section": "responsibilities",
                "item_index": 0,
                "text": "Responsibility: Build microservices",
                "embedding": make_vector(1.0),
            },
            {
                "section": "experience_requirements",
                "item_index": 0,
                "text": "Minimum experience: 2 years",
                "embedding": make_vector(1.0),
            },
            {
                "section": "tools_and_technologies",
                "item_index": 0,
                "text": "Tool or technology: Docker",
                "embedding": make_vector(1.0),
            },
        ],
    }

    # Synthetic Resume
    synthetic_resume_dict = {
        "_id": "mock_upload_001:mock_resume.pdf",
        "upload_id": "mock_upload_001",
        "filename": "mock_resume.pdf",
        "file_path": "/tmp/mock_resume.pdf",
        "file_extension": ".pdf",
        "relative_path": "mock_resume.pdf",
        "status": "completed",
        "resume_data": {
            "skills": ["python", "docker"],
            "projects": [
                {
                    "name": "Microservice Engine",
                    "description": "Built backend services using Docker",
                    "technologies": ["Python", "Docker"],
                }
            ],
            "experience": [
                {
                    "company": "Fintech Corp",
                    "role": "Backend Engineer",
                    "start_date": "2021-01",
                    "end_date": "2024-01",
                    "description": "Developed microservices in Python",
                }
            ],
            "education": [],
            "certifications": [],
            "achievements": [],
            "interests": [],
        },
    }

    # Synthetic Resume Embeddings
    synthetic_resume_embeddings = {
        "_id": "mock_upload_001:mock_resume.pdf",
        "upload_id": "mock_upload_001",
        "filename": "mock_resume.pdf",
        "embeddings": [
            {
                "section": "skills",
                "item_index": 0,
                "text": "Skill: Python",
                "embedding": make_vector(1.0),
            },
            {
                "section": "projects",
                "item_index": 0,
                "text": "Project: Microservice Engine",
                "embedding": make_vector(0.85),
            },
            {
                "section": "experience",
                "item_index": 0,
                "text": "Role: Backend Engineer | Work: Developed microservices",
                "embedding": make_vector(0.75),
            },
        ],
    }

    # Mock the DB calls so this test is completely in-memory and non-destructive
    with (
        patch(
            "app.services.hybrid_matching_service.jd_repository.get",
            new_callable=AsyncMock,
            return_value=synthetic_jd_dict,
        ),
        patch(
            "app.services.hybrid_matching_service.jd_embedding_repository.get_by_jd_id",
            new_callable=AsyncMock,
            return_value=synthetic_jd_embeddings,
        ),
        patch(
            "app.services.hybrid_matching_service.resume_repository.get",
            new_callable=AsyncMock,
            return_value=synthetic_resume_dict,
        ),
        patch(
            "app.services.hybrid_matching_service.resume_embedding_repository.get",
            new_callable=AsyncMock,
            return_value=synthetic_resume_embeddings,
        ),
        patch(
            "app.services.hybrid_matching_service.experience_llm_service.evaluate_experiences",
            new_callable=AsyncMock,
        ) as mock_exp_llm,
    ):
        from app.schemas.experience_relevance import (
            ExperienceRelevanceDecision,
            ExperienceRelevanceResult,
        )

        mock_exp_llm.return_value = ExperienceRelevanceResult(
            experience_decisions=[
                ExperienceRelevanceDecision(
                    experience_index=0,
                    decision="RELEVANT",
                    matched_domains=["Fintech"],
                    matched_context=["microservices"],
                    reason="Matched fintech microservices work",
                )
            ]
        )

        result = await hybrid_matching_service.match_resume(
            jd_id="mock_jd_001",
            upload_id="mock_upload_001",
            filename="mock_resume.pdf",
        )

    # 1. Structure assertions
    assert "exact_matching" in result
    assert "semantic_retrieval" in result
    assert "experience_matching" in result

    sem = result["semantic_retrieval"]
    assert "responsibilities_retrieval" in sem
    assert "tools_and_technologies_retrieval" in sem

    # 2. Responsibilities retrieval check
    resp_results = sem["responsibilities_retrieval"]["results"]
    assert len(resp_results) == 1
    assert resp_results[0]["jd_section"] == "responsibilities"
    for match in resp_results[0]["matches"]:
        assert match["resume_section"] in {"projects", "experience"}

    # 3. Tools and technologies retrieval check
    tools_results = sem["tools_and_technologies_retrieval"]["results"]
    assert len(tools_results) == 1
    assert tools_results[0]["jd_section"] == "tools_and_technologies"
    for match in tools_results[0]["matches"]:
        assert match["resume_section"] == "projects"
        assert match["resume_section"] != "skills"
        assert match["resume_section"] != "experience"

    # 4. Exclusion of required_skills and experience_requirements from semantic retrieval
    all_jd_sections_in_retrieval = {
        item["jd_section"]
        for item in (resp_results + tools_results)
    }
    assert "required_skills" not in all_jd_sections_in_retrieval
    assert "experience_requirements" not in all_jd_sections_in_retrieval

    # 5. Exact matching remains separate and functional (Python matched, FastAPI unmatched against docker)
    assert result["exact_matching"]["matched_required_skills"] == 1
    assert result["exact_matching"]["unmatched_required_skills"] == 1

    # 6. Experience matching remains separate and functional
    assert result["experience_matching"]["relevant_experience_found"] is True

    # 7. No ranking, scoring, or shortlist decisions in output
    disallowed_keys = {
        "final_score",
        "candidate_score",
        "rank",
        "ranking",
        "shortlist",
        "is_shortlisted",
        "decision",
        "pass",
        "hiring_decision",
    }
    assert not disallowed_keys.intersection(result.keys()), (
        f"Found premature ranking/scoring keys: {disallowed_keys.intersection(result.keys())}"
    )

    print_status(
        "Hybrid service correctly separates responsibilities and tools, excludes required_skills/experience, and avoids premature ranking",
        True,
    )


# ==============================================================================
# TEST H: MINIMUM SIMILARITY THRESHOLD CALIBRATION (0.65)
# ==============================================================================


def test_h_threshold_calibration():
    print("\n" + "=" * 70)
    print("TEST H: SIMILARITY THRESHOLD CALIBRATION (0.65 BOUNDARY)")
    print("=" * 70)

    jd_evidence = {
        "section": "tools_and_technologies",
        "item_index": 0,
        "text": "Tool or technology: Docker",
        "embedding": make_vector(1.0),
    }

    # 1. Test exact boundary conditions: 0.65 retained, 0.6499 excluded, 0.6501 retained
    boundary_embeddings = [
        {
            "section": "projects",
            "item_index": 0,
            "text": "Project Exactly At Boundary",
            "embedding": make_vector(0.65),
        },
        {
            "section": "projects",
            "item_index": 1,
            "text": "Project Just Below Boundary",
            "embedding": make_vector(0.6499),
        },
        {
            "section": "projects",
            "item_index": 2,
            "text": "Project Just Above Boundary",
            "embedding": make_vector(0.6501),
        },
        {
            "section": "projects",
            "item_index": 3,
            "text": "Project Clearly Sub-threshold (Noise)",
            "embedding": make_vector(0.53),
        },
        {
            "section": "projects",
            "item_index": 4,
            "text": "Project High Similarity",
            "embedding": make_vector(0.85),
        },
    ]

    matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=boundary_embeddings,
        top_k=5,
    )

    # Must retain 0.85, 0.6501, 0.65; must exclude 0.6499 and 0.53
    assert len(matches) == 3, f"Expected 3 matches, got {len(matches)}"

    # 2. Assert results remain strictly sorted descending
    sims = [m["similarity"] for m in matches]
    assert abs(sims[0] - 0.85) < 1e-4
    assert abs(sims[1] - 0.6501) < 1e-4
    assert abs(sims[2] - 0.65) < 1e-4
    assert sims == sorted(sims, reverse=True)

    # 3. Filtering happens BEFORE top_k is applied (no padding with low-scoring items)
    # Even with top_k=10, only 3 qualifying items should be returned
    matches_large_k = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=boundary_embeddings,
        top_k=10,
    )
    assert len(matches_large_k) == 3, (
        f"Expected 3 matches with top_k=10, got {len(matches_large_k)}"
    )

    # 4. Empty result returned when all candidates fall below threshold
    sub_threshold_embeddings = [
        {
            "section": "projects",
            "item_index": 0,
            "text": "Project A",
            "embedding": make_vector(0.64),
        },
        {
            "section": "projects",
            "item_index": 1,
            "text": "Project B",
            "embedding": make_vector(0.52),
        },
    ]
    empty_matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=sub_threshold_embeddings,
        top_k=5,
    )
    assert empty_matches == [], f"Expected empty list, got {empty_matches}"

    # 5. Configurable threshold parameter override
    override_matches = semantic_retrieval_service.retrieve_for_jd_evidence(
        jd_evidence=jd_evidence,
        resume_embeddings=boundary_embeddings,
        top_k=5,
        min_similarity_threshold=0.80,
    )
    assert len(override_matches) == 1
    assert abs(override_matches[0]["similarity"] - 0.85) < 1e-4

    # 6. Full provenance preserved on thresholded matches
    expected_keys = {
        "jd_section",
        "jd_item_index",
        "jd_text",
        "resume_section",
        "resume_item_index",
        "resume_text",
        "similarity",
    }
    for m in matches:
        assert expected_keys.issubset(m.keys())

    print_status(
        "Similarity threshold (0.65) correctly filters sub-threshold items, retains boundary, and sorts descending",
        True,
    )


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================


async def main():
    print("=" * 80)
    print("TALENTAI — PHASE 5 SEMANTIC RETRIEVAL REGRESSION SUITE")
    print("=" * 80)

    test_a_responsibilities()
    test_b_tools_and_technologies()
    await test_c_required_skills()
    test_d_experience_requirements()
    test_e_provenance_and_top_k()
    test_f_empty_and_unknown_sections()
    await test_g_hybrid_orchestration()
    test_h_threshold_calibration()

    print("\n" + "=" * 80)
    print("ALL TESTS (A through H) PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
