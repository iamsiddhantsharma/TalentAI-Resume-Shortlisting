"""
TalentAI — Phase 5: LLM Required Skills Matching Test Suite

Verifies:
1. Equivalent skills with different wording / abbreviations match.
2. Invalid matches (e.g. AWS vs Pandas, Docker vs Kubernetes) are rejected.
3. Cross-domain requirements (Electrical, Mechanical, Civil, Finance, Healthcare) match accurately.
4. Every JD skill receives exactly one result and counts are mathematically sound.
5. Strict anti-hallucination guard: invented skills not in candidate resume are rejected.
6. Safe handling of invalid JSON and LLM service failures.
7. Exactly one LLM request is made per candidate resume.
8. Preservation of other matching components (responsibilities, tools, experience).
9. API response contracts and strict Phase 6 boundary enforcement (zero ranking/scoring fields).
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.matching import ExactMatchingResult
from app.schemas.resume_object import Experience, Project, ResumeObject
from app.services.experience_matching_service import experience_matching_service
from app.services.hybrid_matching_service import hybrid_matching_service
from app.services.llm_service import llm_service
from app.services.llm_skill_matching_service import (
    LLMSkillMatchingService,
    llm_skill_matching_service,
)
from app.services.semantic_retrieval_service import semantic_retrieval_service


def print_status(test_name: str, passed: bool) -> None:
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {test_name}")


# ==============================================================================
# TEST 1: Equivalent Skills with Different Wording
# ==============================================================================


async def test_1_equivalent_skills_different_wording():
    print("\n" + "=" * 70)
    print("TEST 1: EQUIVALENT SKILLS WITH DIFFERENT WORDING / ABBREVIATIONS")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=[
            "Kubernetes",
            "PostgreSQL",
            "Amazon Web Services",
            "Node.js",
            "Golang",
            "Scikit-Learn",
        ],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    resume = ResumeObject(
        name="Candidate Tech Equivalent",
        skills=[
            "k8s",
            "Postgres",
            "AWS",
            "NodeJS",
            "Go",
            "sklearn",
        ],
        projects=[],
        experience=[],
    )

    t0 = time.perf_counter()
    result = await llm_skill_matching_service.match_required_skills(jd, resume)
    elapsed = time.perf_counter() - t0

    assert result["total_required_skills"] == 6
    assert result["matched_required_skills"] == 6, (
        f"Expected 6 matched, got {result['matched_required_skills']}"
    )
    assert result["unmatched_required_skills"] == 0

    matches_by_req = {m["required_skill"]: m for m in result["matches"]}
    expected_pairs = {
        "Kubernetes": "k8s",
        "PostgreSQL": "Postgres",
        "Amazon Web Services": "AWS",
        "Node.js": "NodeJS",
        "Golang": "Go",
        "Scikit-Learn": "sklearn",
    }

    for req, exp_res in expected_pairs.items():
        item = matches_by_req[req]
        assert item["matched"] is True, f"Expected {req} to match {exp_res}"
        assert item["resume_skill"].lower() == exp_res.lower(), (
            f"Expected resume_skill '{exp_res}', got '{item['resume_skill']}'"
        )
        assert item["match_type"] == "llm"
        print(f"  [MATCHED] {req:<25} -> {item['resume_skill']}")

    print(f"  Latency: {elapsed:.2f}s")
    print_status("Equivalent skills with different wording match successfully", True)


# ==============================================================================
# TEST 2: Invalid Matches Rejected (AWS vs Pandas, Docker vs Kubernetes)
# ==============================================================================


async def test_2_invalid_matches_rejected():
    print("\n" + "=" * 70)
    print("TEST 2: INVALID MATCHES REJECTED (AWS vs Pandas, Docker vs K8s)")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=[
            "AWS",
            "Docker",
            "Java",
            "Python",
            "SQL",
            "Machine Learning",
        ],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    # Candidate has skills in related ecosystems but NOT the required skills
    resume = ResumeObject(
        name="Candidate Non Equivalent",
        skills=[
            "Pandas",       # NOT AWS
            "Kubernetes",   # NOT Docker
            "JavaScript",   # NOT Java
            "C++",          # NOT Python
            "MongoDB",      # NOT SQL (relational)
            "Deep Learning",# NOT classical Machine Learning
        ],
        projects=[],
        experience=[],
    )

    result = await llm_skill_matching_service.match_required_skills(jd, resume)

    matches_by_req = {m["required_skill"]: m for m in result["matches"]}

    assert matches_by_req["AWS"]["matched"] is False, "AWS must not match Pandas"
    assert matches_by_req["AWS"]["resume_skill"] is None

    assert matches_by_req["Docker"]["matched"] is False, "Docker must not match Kubernetes"
    assert matches_by_req["Docker"]["resume_skill"] is None

    assert matches_by_req["Java"]["matched"] is False, "Java must not match JavaScript"
    assert matches_by_req["Java"]["resume_skill"] is None

    assert matches_by_req["Python"]["matched"] is False, "Python must not match C++"
    assert matches_by_req["Python"]["resume_skill"] is None

    assert matches_by_req["SQL"]["matched"] is False, "SQL must not match MongoDB"
    assert matches_by_req["SQL"]["resume_skill"] is None

    assert matches_by_req["Machine Learning"]["matched"] is False, "ML must not match Deep Learning"
    assert matches_by_req["Machine Learning"]["resume_skill"] is None

    for req in jd.required_skills:
        item = matches_by_req[req]
        print(f"  [REJECTED] {req:<20} matched={item['matched']} resume_skill={item['resume_skill']}")

    print_status("Invalid related-but-not-equivalent matches correctly rejected", True)


# ==============================================================================
# TEST 3: Multi-Domain Roles (Electrical, Mechanical, Civil, Finance, Healthcare)
# ==============================================================================


async def test_3_cross_domain_roles():
    print("\n" + "=" * 70)
    print("TEST 3: MULTI-DOMAIN ROLES (ELECTRICAL, MECHANICAL, CIVIL, FINANCE, HEALTHCARE)")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=[
            # Electrical Engineering
            "Programmable Logic Controllers",
            # Mechanical Engineering
            "HVAC",
            # Civil Engineering
            "Computer-Aided Design",
            # Finance
            "Discounted Cash Flow",
            # Healthcare
            "Electrocardiogram interpretation",
            # Unmatched control
            "Pediatric Oncology",
        ],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    resume = ResumeObject(
        name="Multi-Domain Professional",
        skills=[
            "PLC",
            "Heating, Ventilation, and Air Conditioning",
            "CAD drafting",
            "DCF modeling",
            "ECG analysis",
            "Emergency Nursing",  # does not match Pediatric Oncology
        ],
        projects=[],
        experience=[],
    )

    result = await llm_skill_matching_service.match_required_skills(jd, resume)

    assert result["total_required_skills"] == 6
    assert result["matched_required_skills"] == 5
    assert result["unmatched_required_skills"] == 1

    matches_by_req = {m["required_skill"]: m for m in result["matches"]}

    assert matches_by_req["Programmable Logic Controllers"]["matched"] is True
    assert matches_by_req["HVAC"]["matched"] is True
    assert matches_by_req["Computer-Aided Design"]["matched"] is True
    assert matches_by_req["Discounted Cash Flow"]["matched"] is True
    assert matches_by_req["Electrocardiogram interpretation"]["matched"] is True
    assert matches_by_req["Pediatric Oncology"]["matched"] is False

    for req in jd.required_skills:
        item = matches_by_req[req]
        status_label = "MATCHED" if item["matched"] else "UNMATCHED"
        print(f"  [{status_label:<9}] {req:<35} -> {item['resume_skill']}")

    print_status("Cross-domain engineering, finance, and medical skills evaluated accurately", True)


# ==============================================================================
# TEST 4: Every JD Skill Receives Exactly One Result
# ==============================================================================


async def test_4_every_jd_skill_receives_exactly_one_result():
    print("\n" + "=" * 70)
    print("TEST 4: EVERY JD SKILL RECEIVES EXACTLY ONE RESULT")
    print("=" * 70)

    skills = ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis", "Kafka", "AWS"]
    jd = JobDescriptionObject(
        required_skills=skills,
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    resume = ResumeObject(
        name="Candidate Partial",
        skills=["python", "postgres", "redis"],
        projects=[],
        experience=[],
    )

    result = await llm_skill_matching_service.match_required_skills(jd, resume)

    assert result["total_required_skills"] == len(skills)
    assert len(result["matches"]) == len(skills)
    assert result["matched_required_skills"] + result["unmatched_required_skills"] == len(skills)

    returned_reqs = [m["required_skill"] for m in result["matches"]]
    assert returned_reqs == skills, "Returned skills must strictly preserve JD list order and text"

    print(f"  Total requirements: {result['total_required_skills']}")
    print(f"  Matched: {result['matched_required_skills']}")
    print(f"  Unmatched: {result['unmatched_required_skills']}")
    print_status("Every JD skill receives exactly one result with preserved provenance", True)


# ==============================================================================
# TEST 5: Strict Anti-Hallucination Guard
# ==============================================================================


async def test_5_anti_hallucination_defense():
    print("\n" + "=" * 70)
    print("TEST 5: ANTI-HALLUCINATION DEFENSE")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=["AWS", "Python"],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    # Candidate ONLY has Python on resume
    resume = ResumeObject(
        name="Candidate Single Skill",
        skills=["Python"],
        projects=[],
        experience=[],
    )

    # Simulate an LLM that hallucinates and claims AWS matched with an invented skill
    from app.services.llm_skill_matching_service import (
        LLMSkillMatchingOutput,
        SingleSkillDecision,
    )

    hallucinated_output = LLMSkillMatchingOutput(
        skill_decisions=[
            SingleSkillDecision(
                required_skill="AWS",
                matched=True,
                resume_skill="AWS Certified Solutions Architect",  # NOT in resume.skills!
                reason="Hallucinated candidate certification",
            ),
            SingleSkillDecision(
                required_skill="Python",
                matched=True,
                resume_skill="Python",  # Valid
                reason="Direct match",
            ),
        ]
    )

    with patch.object(llm_service, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = hallucinated_output.model_dump(mode="json")

        result = await llm_skill_matching_service.match_required_skills(jd, resume)

    matches_by_req = {m["required_skill"]: m for m in result["matches"]}

    # AWS must be REJECTED because "AWS Certified Solutions Architect" is not in resume.skills
    assert matches_by_req["AWS"]["matched"] is False, "Hallucinated skill must be rejected"
    assert matches_by_req["AWS"]["resume_skill"] is None
    assert matches_by_req["AWS"]["retrieved_skill"] == "AWS Certified Solutions Architect"

    # Python is genuinely on resume, so it must be ACCEPTED
    assert matches_by_req["Python"]["matched"] is True
    assert matches_by_req["Python"]["resume_skill"] == "Python"

    assert result["matched_required_skills"] == 1
    assert result["unmatched_required_skills"] == 1

    print("  [HALLUCINATION REJECTED] AWS -> resume_skill set to null (unmatched=True)")
    print("  [GENUINE ACCEPTED]       Python -> resume_skill preserved")
    print_status("Python validation strictly rejects hallucinated skills not in candidate resume", True)


# ==============================================================================
# TEST 6: Safe Handling of Invalid JSON and LLM Failures
# ==============================================================================


async def test_6_invalid_json_and_llm_failures_handled_safely():
    print("\n" + "=" * 70)
    print("TEST 6: SAFE HANDLING OF INVALID JSON AND LLM SERVICE FAILURES")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=["C++", "Qt", "Linux"],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    resume = ResumeObject(
        name="Candidate Resilient",
        skills=["C++", "Qt"],
        projects=[],
        experience=[],
    )

    # 1. Simulate JSONDecodeError / invalid JSON from LLM
    with patch.object(llm_service, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = ValueError("Ollama returned invalid JSON: Expecting property name enclosed in double quotes")

        result = await llm_skill_matching_service.match_required_skills(jd, resume)

        assert result["total_required_skills"] == 3
        assert result["matched_required_skills"] == 0
        assert result["unmatched_required_skills"] == 3
        assert result["status"] == "failed", f"Expected status 'failed', got {result.get('status')}"
        assert "error" in result and "invalid JSON" in result["error"]
        assert len(result["matches"]) == 3
        for m in result["matches"]:
            assert m["matched"] is False
            assert m["resume_skill"] is None

    print("  Case A: Invalid JSON exception caught cleanly -> status='failed' propagated")

    # 2. Simulate network timeout
    with patch.object(llm_service, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = TimeoutError("Ollama read timeout after 300s")

        result = await llm_skill_matching_service.match_required_skills(jd, resume)

        assert result["total_required_skills"] == 3
        assert result["matched_required_skills"] == 0
        assert result["unmatched_required_skills"] == 3
        assert result["status"] == "failed"
        assert "error" in result and "timeout" in result["error"].lower()

    print("  Case B: Connection timeout caught cleanly -> status='failed' propagated")

    # 3. Simulate connection failure / unreachable LLM
    with patch.object(llm_service, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = ConnectionError("Failed to connect to Ollama on http://localhost:11434")

        result = await llm_skill_matching_service.match_required_skills(jd, resume)

        assert result["total_required_skills"] == 3
        assert result["matched_required_skills"] == 0
        assert result["status"] == "failed"
        assert "error" in result and "Failed to connect" in result["error"]

    print("  Case C: Connection failure caught cleanly -> status='failed' propagated")

    # 4. Simulate malformed model output (fails schema validation)
    with patch.object(llm_service, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"unrecognized_schema": 42}

        result = await llm_skill_matching_service.match_required_skills(jd, resume)

        assert result["total_required_skills"] == 3
        assert result["matched_required_skills"] == 0
        assert result["status"] == "failed"
        assert "error" in result and "validation" in result["error"].lower()

    print("  Case D: Malformed model output caught cleanly -> status='failed' propagated")

    # 5. Empty resume skills: valid empty evidence, NOT an LLM failure
    resume_empty = ResumeObject(
        name="Candidate Empty Skills",
        skills=[],
        projects=[],
        experience=[],
    )
    result_empty = await llm_skill_matching_service.match_required_skills(jd, resume_empty)
    assert result_empty["total_required_skills"] == 3
    assert result_empty["matched_required_skills"] == 0
    assert result_empty["unmatched_required_skills"] == 3
    assert result_empty["status"] == "completed", f"Expected completed status, got {result_empty.get('status')}"
    assert result_empty.get("error") is None
    print("  Case E: Empty candidate resume skills -> status='completed', error=None (valid empty evidence)")

    # 6. Successful assessment with zero matches
    from app.services.llm_skill_matching_service import (
        LLMSkillMatchingOutput,
        SingleSkillDecision,
    )
    decisions_zero = [
        SingleSkillDecision(required_skill=s, matched=False, resume_skill=None, reason="No match")
        for s in ["C++", "Qt", "Linux"]
    ]
    with patch.object(llm_service, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = LLMSkillMatchingOutput(skill_decisions=decisions_zero).model_dump(mode="json")

        result_zero = await llm_skill_matching_service.match_required_skills(jd, resume)

        assert result_zero["total_required_skills"] == 3
        assert result_zero["matched_required_skills"] == 0
        assert result_zero["unmatched_required_skills"] == 3
        assert result_zero["status"] == "completed"
        assert result_zero.get("error") is None
    print("  Case F: Successful evaluation with 0 matches -> status='completed', error=None")
    print_status("LLM failures properly distinguished from valid zero matches and empty skills", True)


# ==============================================================================
# TEST 7: Exactly One LLM Request per Resume
# ==============================================================================


async def test_7_exactly_one_llm_request_per_resume():
    print("\n" + "=" * 70)
    print("TEST 7: EXACTLY ONE LLM REQUEST PER RESUME")
    print("=" * 70)

    skills = [f"Skill_{i}" for i in range(15)]
    jd = JobDescriptionObject(
        required_skills=skills,
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    resume = ResumeObject(
        name="Candidate Bulk",
        skills=["Skill_1", "Skill_5", "Skill_10"],
        projects=[],
        experience=[],
    )

    from app.services.llm_skill_matching_service import (
        LLMSkillMatchingOutput,
        SingleSkillDecision,
    )

    mock_decisions = [
        SingleSkillDecision(
            required_skill=s,
            matched=(s in resume.skills),
            resume_skill=s if s in resume.skills else None,
            reason="Matched" if s in resume.skills else "Unmatched",
        )
        for s in skills
    ]

    with patch.object(llm_service, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = LLMSkillMatchingOutput(
            skill_decisions=mock_decisions
        ).model_dump(mode="json")

        result = await llm_skill_matching_service.match_required_skills(jd, resume)

        assert mock_llm.call_count == 1, (
            f"Expected exactly 1 LLM request for the resume, got {mock_llm.call_count}"
        )

    assert result["total_required_skills"] == 15
    assert result["matched_required_skills"] == 3
    assert result["unmatched_required_skills"] == 12

    print(f"  Evaluated 15 skills in exactly {mock_llm.call_count} LLM request.")
    print_status("Exactly one compact LLM request executed per resume", True)


# ==============================================================================
# TEST 8: Preservation of Other Matching Components
# ==============================================================================


def test_8_preservation_of_other_matching_components():
    print("\n" + "=" * 70)
    print("TEST 8: PRESERVATION OF OTHER MATCHING COMPONENTS")
    print("=" * 70)

    # 1. Responsibilities section mapping & threshold
    assert semantic_retrieval_service.SECTION_MAPPING["responsibilities"] == {
        "projects",
        "experience",
    }
    assert semantic_retrieval_service.DEFAULT_MIN_SIMILARITY_THRESHOLD == 0.65

    # 2. Tools section mapping & threshold
    assert semantic_retrieval_service.SECTION_MAPPING["tools_and_technologies"] == {
        "projects",
    }

    # 3. Required skills and experience requirements excluded from semantic retrieval
    assert semantic_retrieval_service.get_allowed_resume_sections("required_skills") == set()
    assert semantic_retrieval_service.get_allowed_resume_sections("experience_requirements") == set()

    # 4. Experience matching service methods and ongoing keywords intact
    assert "present" in experience_matching_service.ONGOING_KEYWORDS
    assert "current" in experience_matching_service.ONGOING_KEYWORDS
    assert hasattr(experience_matching_service, "merge_overlapping_periods")
    assert hasattr(experience_matching_service, "evaluate_duration_requirement")

    print_status("Responsibilities, tools, experience, and retrieval boundaries 100% preserved", True)


# ==============================================================================
# TEST 9: API Response Contracts and Phase 6 Boundary Enforcement
# ==============================================================================


async def test_9_api_contracts_and_phase_6_boundaries():
    print("\n" + "=" * 70)
    print("TEST 9: API CONTRACTS AND PHASE 6 BOUNDARIES")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=["Python", "FastAPI"],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    resume = ResumeObject(
        name="Candidate Contract",
        skills=["Python"],
        projects=[],
        experience=[],
    )

    raw_result = await llm_skill_matching_service.match_required_skills(jd, resume)

    # 1. Output must validate cleanly against ExactMatchingResult Pydantic schema
    validated = ExactMatchingResult.model_validate(raw_result)
    assert validated.total_required_skills == 2
    assert validated.matched_required_skills == 1
    assert validated.unmatched_required_skills == 1
    assert len(validated.matches) == 2

    # 2. Phase 6 boundary enforcement: no ranking or scoring keys
    forbidden_keys = {
        "score",
        "final_score",
        "rank",
        "shortlisted",
        "percentile",
        "weight",
        "hiring_decision",
    }
    for match_item in raw_result["matches"]:
        for k in match_item:
            assert k not in forbidden_keys, f"Forbidden Phase 6 key '{k}' found in match item"
    for k in raw_result:
        assert k not in forbidden_keys, f"Forbidden Phase 6 key '{k}' found in result dict"

    print("  Validated cleanly against ExactMatchingResult schema.")
    print("  Zero forbidden scoring/ranking keys present.")
    print_status("API contract compatibility and Phase 6 boundaries verified", True)


# ==============================================================================
# TEST 10: ZERO LEGACY MATCHING OR TAXONOMY DEPENDENCIES
# ==============================================================================


def test_10_no_legacy_matching_or_taxonomy_dependencies():
    print("\n" + "=" * 70)
    print("TEST 10: ZERO LEGACY MATCHING OR TAXONOMY DEPENDENCIES")
    print("=" * 70)

    # 1. Verify llm_skill_matching_service does not import or use any taxonomy or alias dictionaries
    import app.services.llm_skill_matching_service as llm_service_module

    assert not hasattr(llm_service_module, "SKILL_TAXONOMY"), "No taxonomy dictionary in LLM service"
    assert not hasattr(llm_service_module, "CANONICAL_SKILL_MAP"), "No canonical alias map in LLM service"
    assert not hasattr(llm_service_module, "ALLOWED_COMPATIBLE_PAIRS"), "No compatibility matrix in LLM service"
    assert not hasattr(llm_service_module, "FORBIDDEN_CROSS_DOMAIN_PAIRS"), "No forbidden pairs in LLM service"
    assert not hasattr(llm_service_module, "verify_semantic_skill_match"), "No legacy verification engine"

    # 2. Verify hybrid_matching_service exclusively imports llm_skill_matching_service for required skills
    import app.services.hybrid_matching_service as hybrid_module

    assert hasattr(hybrid_module, "llm_skill_matching_service"), "hybrid_matching_service must import llm_skill_matching_service"
    assert not hasattr(hybrid_module, "exact_matching_service"), "hybrid_matching_service must NOT import exact_matching_service"

    # 3. Verify no cosine similarity threshold or embedding calculation in LLM service instance
    service_inst = llm_service_module.llm_skill_matching_service
    assert not hasattr(service_inst, "min_similarity_threshold")
    assert not hasattr(service_inst, "embedding_service")
    assert not hasattr(service_inst, "_embedding_cache")

    print("  Verified: No taxonomy, alias map, or cosine threshold dependencies exist.")
    print_status("Zero legacy matching or taxonomy dependencies in active pipeline", True)


# ==============================================================================
# TEST 11: Capability-Based Matches Rejected (TensorFlow vs CNN, Keras vs LSTM, Flask vs Model Deployment, K-Means vs Unsupervised Learning)
# ==============================================================================


async def test_11_capability_based_matches_rejected():
    print("\n" + "=" * 70)
    print("TEST 11: CAPABILITY-BASED FALSE POSITIVES REJECTED")
    print("=" * 70)

    jd = JobDescriptionObject(
        required_skills=[
            "CNN",
            "LSTM",
            "Model Deployment",
            "Unsupervised Learning",
            "Computer Vision",
            "Natural Language Processing",
            "Convolutional Neural Networks",
            "Long Short-Term Memory",
            "CV",
            "NLP",
            "Model Serving",
        ],
        responsibilities=[],
        experience_requirements=[],
        tools_and_technologies=[],
    )

    resume = ResumeObject(
        name="Candidate Capability Library",
        skills=[
            "TensorFlow",
            "Keras",
            "Flask",
            "Django",
            "K-Means",
            "OpenCV",
            "NLTK",
            "Python",
            "Pandas",
        ],
        projects=[],
        experience=[],
    )

    # Mock LLM output that attempts to match capability-based false positives
    from app.services.llm_skill_matching_service import LLMSkillMatchingOutput, SingleSkillDecision
    mock_output = LLMSkillMatchingOutput(
        skill_decisions=[
            SingleSkillDecision(required_skill="CNN", matched=True, resume_skill="TensorFlow", reason="TF can train CNNs"),
            SingleSkillDecision(required_skill="Convolutional Neural Networks", matched=True, resume_skill="Keras", reason="Keras has Conv layers"),
            SingleSkillDecision(required_skill="LSTM", matched=True, resume_skill="Keras", reason="Keras has LSTM layers"),
            SingleSkillDecision(required_skill="Long Short-Term Memory", matched=True, resume_skill="TensorFlow", reason="TF has LSTM"),
            SingleSkillDecision(required_skill="Model Deployment", matched=True, resume_skill="Flask", reason="Flask serves models"),
            SingleSkillDecision(required_skill="Model Serving", matched=True, resume_skill="Django", reason="Django can serve models"),
            SingleSkillDecision(required_skill="Unsupervised Learning", matched=True, resume_skill="K-Means", reason="K-Means is clustering"),
            SingleSkillDecision(required_skill="CV", matched=True, resume_skill="Python", reason="Python used for CV"),
            SingleSkillDecision(required_skill="NLP", matched=True, resume_skill="Pandas", reason="Pandas used for data"),
            SingleSkillDecision(required_skill="Computer Vision", matched=True, resume_skill="OpenCV", reason="OpenCV is computer vision"),
            SingleSkillDecision(required_skill="Natural Language Processing", matched=True, resume_skill="NLTK", reason="NLTK is NLP"),
        ]
    )

    with patch.object(llm_service, "generate_json", new=AsyncMock(return_value=mock_output.model_dump())):
        result = await llm_skill_matching_service.match_required_skills(jd, resume)

    matches_by_req = {m["required_skill"]: m for m in result["matches"]}

    # Verify capability-based matches were rejected by Python post-validation
    assert matches_by_req["CNN"]["matched"] is False, "TensorFlow must NOT qualify for CNN"
    assert matches_by_req["CNN"]["resume_skill"] is None
    print("  [REJECTED] CNN -> TensorFlow (general framework does not prove CNN expertise)")

    assert matches_by_req["Convolutional Neural Networks"]["matched"] is False, "Keras must NOT qualify for CNN"
    assert matches_by_req["Convolutional Neural Networks"]["resume_skill"] is None
    print("  [REJECTED] Convolutional Neural Networks -> Keras (general library does not prove CNN expertise)")

    assert matches_by_req["LSTM"]["matched"] is False, "Keras must NOT qualify for LSTM"
    assert matches_by_req["LSTM"]["resume_skill"] is None
    print("  [REJECTED] LSTM -> Keras (general library does not prove LSTM expertise)")

    assert matches_by_req["Long Short-Term Memory"]["matched"] is False, "TensorFlow must NOT qualify for LSTM"
    assert matches_by_req["Long Short-Term Memory"]["resume_skill"] is None
    print("  [REJECTED] Long Short-Term Memory -> TensorFlow (general framework does not prove LSTM expertise)")

    assert matches_by_req["Model Deployment"]["matched"] is False, "Flask must NOT qualify for Model Deployment"
    assert matches_by_req["Model Deployment"]["resume_skill"] is None
    print("  [REJECTED] Model Deployment -> Flask (web framework does not prove deployment expertise)")

    assert matches_by_req["Model Serving"]["matched"] is False, "Django must NOT qualify for Model Serving"
    assert matches_by_req["Model Serving"]["resume_skill"] is None
    print("  [REJECTED] Model Serving -> Django (web framework does not prove deployment expertise)")

    assert matches_by_req["Unsupervised Learning"]["matched"] is False, "K-Means must NOT qualify for Unsupervised Learning"
    assert matches_by_req["Unsupervised Learning"]["resume_skill"] is None
    print("  [REJECTED] Unsupervised Learning -> K-Means (single algorithm does not substitute for discipline)")

    assert matches_by_req["CV"]["matched"] is False, "Python must NOT qualify for Computer Vision"
    assert matches_by_req["CV"]["resume_skill"] is None
    print("  [REJECTED] CV -> Python (general language does not prove CV expertise)")

    assert matches_by_req["NLP"]["matched"] is False, "Pandas must NOT qualify for NLP"
    assert matches_by_req["NLP"]["resume_skill"] is None
    print("  [REJECTED] NLP -> Pandas (data manipulation library does not prove NLP expertise)")

    # Verify direct equivalent domains are preserved
    assert matches_by_req["Computer Vision"]["matched"] is True, "OpenCV is directly dedicated to Computer Vision"
    assert matches_by_req["Computer Vision"]["resume_skill"] == "OpenCV"
    print("  [MATCHED ] Computer Vision -> OpenCV (direct domain equivalent)")

    assert matches_by_req["Natural Language Processing"]["matched"] is True, "NLTK is directly dedicated to NLP"
    assert matches_by_req["Natural Language Processing"]["resume_skill"] == "NLTK"
    print("  [MATCHED ] Natural Language Processing -> NLTK (direct domain equivalent)")

    assert result["matched_required_skills"] == 2
    assert result["unmatched_required_skills"] == 9
    print_status("Capability-based false positives rejected while preserving direct equivalents", True)


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================


async def main_async():
    print("=" * 80)
    print("TALENTAI — LLM REQUIRED SKILLS MATCHING REGRESSION TEST SUITE")
    print("=" * 80)

    await test_1_equivalent_skills_different_wording()
    await test_2_invalid_matches_rejected()
    await test_3_cross_domain_roles()
    await test_4_every_jd_skill_receives_exactly_one_result()
    await test_5_anti_hallucination_defense()
    await test_6_invalid_json_and_llm_failures_handled_safely()
    await test_7_exactly_one_llm_request_per_resume()
    test_8_preservation_of_other_matching_components()
    await test_9_api_contracts_and_phase_6_boundaries()
    test_10_no_legacy_matching_or_taxonomy_dependencies()
    await test_11_capability_based_matches_rejected()

    print("\n" + "=" * 80)
    print("ALL 11 LLM REQUIRED-SKILLS MATCHING TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()


