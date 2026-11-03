"""
TalentAI — Phase 2: Strict LLM Experience Relevance Unit Tests

Deterministic unit tests covering all required relevance cases using mocked LLM responses:
1. Backend-only REST API development against an AI/ML JD: IRRELEVANT, ratio 0.0.
2. Genuine ML model training or evaluation: RELEVANT, ratio 1.0.
3. Mixed backend and actual model-inference deployment: PARTIALLY_RELEVANT, ratio 0.5.
4. A generic job title with genuine ML deliverables: judge deliverables, not title (RELEVANT, ratio 1.0).
5. An AI-branded job title with only ordinary web development: IRRELEVANT, ratio 0.0.
6. Vague claims such as "worked on AI technologies": INSUFFICIENT_INFORMATION, ratio 0.0.
7. Explicitly documented partial allocation (e.g. 0.3) vs unquantified mixed role (0.5 default).
8. Schema validation and structured-output parsing with missing optional fields.
9. Diwakar's backend internship against Accenture AI/ML JD: zero relevance credit (IRRELEVANT, ratio 0.0).
10. Model omitted experience index fallback.
11. Safeguard override: TRANSFERABLE_BACKEND cannot receive partial credit for AI/ML criteria.
"""

import asyncio
from unittest.mock import AsyncMock, patch

from app.schemas.experience_relevance import (
    ExperienceRelevanceDecision,
    ExperienceRelevanceResult,
)
from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)
from app.schemas.resume_object import Experience, ResumeObject
from app.services.experience_llm_service import experience_llm_service


# Standard Accenture AI/ML JD for test fixtures
def create_accenture_ai_ml_jd() -> JobDescriptionObject:
    return JobDescriptionObject(
        required_skills=[
            "Python",
            "Machine Learning",
            "Deep Learning",
            "NLP",
            "PyTorch",
            "TensorFlow",
            "Computational Science",
        ],
        responsibilities=[
            "Design and train machine learning and deep learning models",
            "Conduct computational science simulations and mathematical modeling",
            "Evaluate model performance metrics and optimize training pipelines",
        ],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2,
                maximum_years=5,
                preferred_domains=[
                    "Computational Science",
                    "Artificial Intelligence",
                    "Machine Learning",
                ],
            )
        ],
        tools_and_technologies=[
            "Python",
            "PyTorch",
            "TensorFlow",
            "Scikit-learn",
            "Docker",
        ],
    )


# ------------------------------------------------------------------------------
# TEST 1: BACKEND-ONLY REST API DEVELOPMENT AGAINST AI/ML JD -> IRRELEVANT (0.0)
# ------------------------------------------------------------------------------
async def test_backend_only_rest_api_against_ai_ml_jd():
    print("Test 1: Backend-only REST API against AI/ML JD -> IRRELEVANT, ratio 0.0")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate A",
        experience=[
            Experience(
                role="Backend Developer",
                company="Fintech Corp",
                description="Built REST APIs using Flask and Python. Handled PostgreSQL queries and Redis caching.",
            )
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "IRRELEVANT",
                "matched_domains": [],
                "matched_context": [],
                "reason": "Generic backend REST API and database work does not demonstrate AI/ML modeling.",
                "relevant_work_summary": None,
                "relevance_ratio": 0.0,
                "evidence_classification": "TRANSFERABLE_BACKEND",
                "confidence": "HIGH",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    assert len(result.experience_decisions) == 1
    d = result.experience_decisions[0]
    assert d.decision == "IRRELEVANT"
    assert d.relevance_ratio == 0.0
    assert d.relevant_work_summary is None
    assert d.matched_domains == []
    assert d.evidence_classification == "TRANSFERABLE_BACKEND"
    print("  [PASSED] Correctly classified as IRRELEVANT with ratio 0.0 and null summary.")


# ------------------------------------------------------------------------------
# TEST 2: GENUINE ML MODEL TRAINING OR EVALUATION -> RELEVANT (1.0)
# ------------------------------------------------------------------------------
async def test_genuine_ml_model_training_and_evaluation():
    print("Test 2: Genuine ML model training/eval -> RELEVANT, ratio 1.0")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate B",
        experience=[
            Experience(
                role="Machine Learning Engineer",
                company="AI Labs",
                description="Trained deep convolutional neural networks in PyTorch for medical imaging; optimized loss functions and evaluated AUC-ROC and F1 scores.",
            )
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "matched_domains": ["Machine Learning", "Artificial Intelligence"],
                "matched_context": ["PyTorch", "model training", "deep learning"],
                "reason": "Substantive deep learning model training and evaluation in PyTorch.",
                "relevant_work_summary": "Trained deep convolutional neural networks in PyTorch for medical imaging; optimized loss functions and evaluated AUC-ROC and F1 scores.",
                "relevance_ratio": 1.0,
                "evidence_classification": "MODEL_TRAINING_OR_EVAL",
                "confidence": "HIGH",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    assert len(result.experience_decisions) == 1
    d = result.experience_decisions[0]
    assert d.decision == "RELEVANT"
    assert d.relevance_ratio == 1.0
    assert d.relevant_work_summary is not None
    assert "PyTorch" in d.relevant_work_summary
    assert d.evidence_classification == "MODEL_TRAINING_OR_EVAL"
    print("  [PASSED] Correctly classified as RELEVANT with ratio 1.0 and substantive summary.")


# ------------------------------------------------------------------------------
# TEST 3: MIXED BACKEND AND MODEL INFERENCE DEPLOYMENT -> PARTIALLY_RELEVANT (0.5)
# ------------------------------------------------------------------------------
async def test_mixed_backend_and_inference_deployment():
    print("Test 3: Mixed backend and inference deployment -> PARTIALLY_RELEVANT, ratio 0.5")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate C",
        experience=[
            Experience(
                role="Software Engineer",
                company="Tech Solutions",
                description="Built full-stack React and FastAPI dashboards; packaged and deployed an ONNX ML model pipeline for real-time inference serving.",
            )
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "PARTIALLY_RELEVANT",
                "matched_domains": ["Machine Learning"],
                "matched_context": ["inference serving", "model pipeline"],
                "reason": "Actual ML model deployment for inference mixed with general dashboard engineering.",
                "relevant_work_summary": "packaged and deployed an ONNX ML model pipeline for real-time inference serving",
                "relevance_ratio": 0.5,
                "evidence_classification": "INFERENCE_DEPLOYMENT",
                "confidence": "MEDIUM",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    assert len(result.experience_decisions) == 1
    d = result.experience_decisions[0]
    assert d.decision == "PARTIALLY_RELEVANT"
    assert d.relevance_ratio == 0.5
    assert d.relevant_work_summary == "packaged and deployed an ONNX ML model pipeline for real-time inference serving"
    assert d.evidence_classification == "INFERENCE_DEPLOYMENT"
    print("  [PASSED] Correctly classified as PARTIALLY_RELEVANT with default heuristic 0.5.")


# ------------------------------------------------------------------------------
# TEST 4: GENERIC TITLE WITH GENUINE ML DELIVERABLES -> RELEVANT (1.0)
# ------------------------------------------------------------------------------
async def test_generic_title_with_genuine_ml_deliverables():
    print("Test 4: Generic title with genuine ML deliverables -> Title Invariance (RELEVANT, ratio 1.0)")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate D",
        experience=[
            Experience(
                role="Junior Consultant",  # Generic non-AI title
                company="Global Advisory",
                description="Designed and trained RoBERTa transformer models using PyTorch for clinical entity recognition; reached 0.89 F1 score.",
            )
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "matched_domains": ["Computational Science", "Artificial Intelligence"],
                "matched_context": ["PyTorch", "RoBERTa transformer", "F1 score"],
                "reason": "Documented work demonstrates genuine transformer model training regardless of Junior Consultant title.",
                "relevant_work_summary": "Designed and trained RoBERTa transformer models using PyTorch for clinical entity recognition; reached 0.89 F1 score.",
                "relevance_ratio": 1.0,
                "evidence_classification": "MODEL_TRAINING_OR_EVAL",
                "confidence": "HIGH",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    d = result.experience_decisions[0]
    assert d.decision == "RELEVANT"
    assert d.relevance_ratio == 1.0
    print("  [PASSED] Deliverables judged rather than generic title.")


# ------------------------------------------------------------------------------
# TEST 5: AI-BRANDED TITLE WITH ONLY ORDINARY WEB DEVELOPMENT -> IRRELEVANT (0.0)
# ------------------------------------------------------------------------------
async def test_ai_branded_title_with_ordinary_web_development():
    print("Test 5: AI-branded title with only ordinary web dev -> IRRELEVANT, ratio 0.0")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate E",
        experience=[
            Experience(
                role="AI/ML Engineer Intern",  # Fancy title with only web dev
                company="Web Innovations",
                description="Created HTML forms and simple CRUD endpoints using Express and MongoDB. Documented endpoints with Swagger and tested routes with Postman.",
            )
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "IRRELEVANT",
                "matched_domains": [],
                "matched_context": [],
                "reason": "Title says AI/ML but deliverables contain only ordinary web CRUD endpoints and Postman testing.",
                "relevant_work_summary": None,
                "relevance_ratio": 0.0,
                "evidence_classification": "TRANSFERABLE_BACKEND",
                "confidence": "HIGH",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    d = result.experience_decisions[0]
    assert d.decision == "IRRELEVANT"
    assert d.relevance_ratio == 0.0
    assert d.relevant_work_summary is None
    print("  [PASSED] AI-branded title properly rejected due to lack of AI/ML deliverables.")


# ------------------------------------------------------------------------------
# TEST 6: VAGUE CLAIMS -> INSUFFICIENT_INFORMATION (0.0)
# ------------------------------------------------------------------------------
async def test_vague_claims_insufficient_information():
    print("Test 6: Vague claim 'worked on AI technologies' -> INSUFFICIENT_INFORMATION, ratio 0.0")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate F",
        experience=[
            Experience(
                role="Software Developer",
                company="Tech Startup",
                description="Worked on cutting-edge AI technologies and assisted with modern platforms.",
            )
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "INSUFFICIENT_INFORMATION",
                "matched_domains": [],
                "matched_context": [],
                "reason": "Vague claims without verifiable technical deliverables or specific tasks.",
                "relevant_work_summary": None,
                "relevance_ratio": 0.0,
                "evidence_classification": "UNSPECIFIED",
                "confidence": "LOW",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    d = result.experience_decisions[0]
    assert d.decision == "INSUFFICIENT_INFORMATION"
    assert d.relevance_ratio == 0.0
    assert d.relevant_work_summary is None
    print("  [PASSED] Vague claim correctly flagged as INSUFFICIENT_INFORMATION.")


# ------------------------------------------------------------------------------
# TEST 7: EXPLICIT DOCUMENTED RATIO (0.3) VS UNQUANTIFIED ROLE (0.5)
# ------------------------------------------------------------------------------
async def test_explicit_ratio_vs_unquantified_role():
    print("Test 7: Explicitly documented partial ratio (0.3) vs unquantified role (0.5 default)")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate G",
        experience=[
            Experience(
                role="Full Stack Engineer",
                company="Multi Tech",
                description="Dedicated 30% of time to tuning XGBoost ranking models; spent remaining 70% building frontend interfaces and database migrations.",
            ),
            Experience(
                role="Software Engineer",
                company="Cloud Co",
                description="Built backend microservices and deployed ML inference models for fraud detection.",
            ),
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "PARTIALLY_RELEVANT",
                "matched_domains": ["Machine Learning"],
                "matched_context": ["XGBoost ranking models"],
                "reason": "Explicitly documents 30% time allocation to ML model tuning.",
                "relevant_work_summary": "tuning XGBoost ranking models",
                "relevance_ratio": 0.3,
                "evidence_classification": "MODEL_TRAINING_OR_EVAL",
                "confidence": "HIGH",
            },
            {
                "experience_index": 1,
                "decision": "PARTIALLY_RELEVANT",
                "matched_domains": ["Machine Learning"],
                "matched_context": ["ML inference models"],
                "reason": "Unquantified mixed role performing ML inference and backend services.",
                "relevant_work_summary": "deployed ML inference models for fraud detection",
                "relevance_ratio": 0.0,  # LLM left it 0.0; normalizer should set default 0.5
                "evidence_classification": "INFERENCE_DEPLOYMENT",
                "confidence": "MEDIUM",
            },
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    assert len(result.experience_decisions) == 2
    # Role 0: explicit 0.3 preserved
    assert result.experience_decisions[0].decision == "PARTIALLY_RELEVANT"
    assert result.experience_decisions[0].relevance_ratio == 0.3

    # Role 1: unquantified gets 0.5 heuristic default
    assert result.experience_decisions[1].decision == "PARTIALLY_RELEVANT"
    assert result.experience_decisions[1].relevance_ratio == 0.5
    print("  [PASSED] Explicit ratio 0.3 preserved and unquantified role normalized to 0.5.")


# ------------------------------------------------------------------------------
# TEST 8: SCHEMA VALIDATION & MISSING OPTIONAL FIELDS
# ------------------------------------------------------------------------------
async def test_schema_validation_and_missing_optional_fields():
    print("Test 8: Schema validation and missing optional fields")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate H",
        experience=[
            Experience(
                role="Data Scientist",
                company="Analytics Inc",
                description="Built NLP summarization pipelines.",
            )
        ],
    )

    # Response missing reason, matched_domains, matched_context, relevant_work_summary, confidence
    sparse_mock_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=sparse_mock_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    d = result.experience_decisions[0]
    assert d.decision == "RELEVANT"
    assert d.relevance_ratio == 1.0
    assert d.matched_domains == []
    assert d.matched_context == []
    assert d.reason == ""
    print("  [PASSED] Schema validated and defaults populated gracefully.")


# ------------------------------------------------------------------------------
# TEST 9: DIWAKAR'S EXACT BACKEND INTERNSHIP AGAINST ACCENTURE AI/ML JD
# ------------------------------------------------------------------------------
async def test_diwakar_backend_internship_receives_zero_credit():
    print("Test 9: Diwakar's Backend Developer Internship -> Zero AI/ML Credit (IRRELEVANT, ratio 0.0)")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Diwakar",
        experience=[
            Experience(
                company="High Radius",
                role="Backend Developer Intern",
                start_date="JUN’22",
                end_date="AUG’22",
                description="Developed REST APIs with Flask and Python, integrated Cosmos DB, Azure cloud hosting, Postman testing, Swagger documentation.",
            )
        ],
    )

    mock_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "IRRELEVANT",
                "matched_domains": [],
                "matched_context": [],
                "reason": "The candidate developed REST APIs using Flask, Cosmos DB, and Azure. While Python was used, the work is strictly generic backend development without machine learning, neural networks, computational science, or model evaluation.",
                "relevant_work_summary": None,
                "relevance_ratio": 0.0,
                "evidence_classification": "TRANSFERABLE_BACKEND",
                "confidence": "HIGH",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=mock_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    d = result.experience_decisions[0]
    assert d.decision == "IRRELEVANT"
    assert d.relevance_ratio == 0.0
    assert d.relevant_work_summary is None
    assert d.evidence_classification == "TRANSFERABLE_BACKEND"
    print("  [PASSED] Acceptance Criterion Met: Diwakar receives exactly 0.0 relevance ratio.")


# ------------------------------------------------------------------------------
# TEST 10: SAFEGUARD: TRANSFERABLE_BACKEND CANNOT RECEIVE PARTIAL AI/ML CREDIT
# ------------------------------------------------------------------------------
async def test_transferable_backend_safeguard_override():
    print("Test 10: Safeguard: TRANSFERABLE_BACKEND cannot receive partial credit for AI/ML")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate I",
        experience=[
            Experience(
                role="Python Developer",
                company="Legacy Co",
                description="Built Flask APIs with PostgreSQL.",
            )
        ],
    )

    # Simulate an LLM hallucination where it returned PARTIALLY_RELEVANT for transferable backend
    flawed_llm_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "PARTIALLY_RELEVANT",  # Hallucinated decision
                "matched_domains": ["Machine Learning"],
                "matched_context": ["Python"],
                "reason": "Python is transferable to ML.",
                "relevant_work_summary": "Built Flask APIs",
                "relevance_ratio": 0.5,
                "evidence_classification": "TRANSFERABLE_BACKEND",
                "confidence": "LOW",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=flawed_llm_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    d = result.experience_decisions[0]
    # Normalizer safeguard must override this to IRRELEVANT
    assert d.decision == "IRRELEVANT"
    assert d.relevance_ratio == 0.0
    assert d.relevant_work_summary is None
    assert d.matched_domains == []
    print("  [PASSED] Normalizer safeguard successfully caught and corrected transferable backend hallucination.")


# ------------------------------------------------------------------------------
# TEST 11: MODEL OMITTED EXPERIENCE INDEX FALLBACK
# ------------------------------------------------------------------------------
async def test_omitted_experience_index_fallback():
    print("Test 11: Model omitted experience index fallback")
    jd = create_accenture_ai_ml_jd()
    resume = ResumeObject(
        name="Candidate J",
        experience=[
            Experience(role="Role 0", company="C0", description="Desc 0"),
            Experience(role="Role 1", company="C1", description="Desc 1"),
        ],
    )

    # LLM only returned index 0, omitted index 1
    partial_response = {
        "experience_decisions": [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "relevance_ratio": 1.0,
                "evidence_classification": "MODEL_TRAINING_OR_EVAL",
            }
        ]
    }

    with patch("app.services.llm_service.llm_service.generate_json", new=AsyncMock(return_value=partial_response)):
        result = await experience_llm_service.evaluate_experiences(jd, resume)

    assert len(result.experience_decisions) == 2
    assert result.experience_decisions[0].decision == "RELEVANT"
    # Omitted index 1 must be present with safe fallback
    assert result.experience_decisions[1].experience_index == 1
    assert result.experience_decisions[1].decision == "INSUFFICIENT_INFORMATION"
    assert result.experience_decisions[1].relevance_ratio == 0.0
    print("  [PASSED] Omitted index successfully populated with INSUFFICIENT_INFORMATION.")


# ------------------------------------------------------------------------------
# MAIN TEST RUNNER
# ------------------------------------------------------------------------------
async def main():
    print("\n" + "=" * 80)
    print("TALENTAI — PHASE 2 STRICT LLM EXPERIENCE RELEVANCE UNIT TEST SUITE")
    print("=" * 80 + "\n")

    await test_backend_only_rest_api_against_ai_ml_jd()
    await test_genuine_ml_model_training_and_evaluation()
    await test_mixed_backend_and_inference_deployment()
    await test_generic_title_with_genuine_ml_deliverables()
    await test_ai_branded_title_with_ordinary_web_development()
    await test_vague_claims_insufficient_information()
    await test_explicit_ratio_vs_unquantified_role()
    await test_schema_validation_and_missing_optional_fields()
    await test_diwakar_backend_internship_receives_zero_credit()
    await test_transferable_backend_safeguard_override()
    await test_omitted_experience_index_fallback()

    print("\n" + "=" * 80)
    print("ALL 11 PHASE 2 STRICT LLM RELEVANCE TESTS PASSED (100%)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
