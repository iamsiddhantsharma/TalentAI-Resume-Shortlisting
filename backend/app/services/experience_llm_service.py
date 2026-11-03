import json
import logging
from typing import Any

from app.schemas.experience_relevance import (
    ExperienceDecision,
    ExperienceRelevanceDecision,
    ExperienceRelevanceResult,
)
from app.schemas.job_description_object import JobDescriptionObject
from app.schemas.resume_object import Experience, ResumeObject
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class ExperienceLLMService:
    """
    Uses Qwen to determine whether each resume experience entry is
    evidence-based and relevant to the experience requirement of a Job Description.

    IMPORTANT:

    This service is ONLY used when the JD actually contains
    a meaningful experience requirement.

    It does NOT:
    - calculate years of experience
    - calculate experience duration
    - parse dates
    - merge overlapping experience
    - compare minimum/maximum years
    - calculate final candidate ranking
    - evaluate general resume quality

    Qwen decides:
        RELEVANT
        PARTIALLY_RELEVANT
        IRRELEVANT
        AMBIGUOUS
        INSUFFICIENT_INFORMATION

    Python deterministically validates and normalizes:
        relevance_ratio (1.0 for RELEVANT, 0.5 default for PARTIALLY_RELEVANT, 0.0 otherwise)
        relevant_work_summary (null for non-relevant/insufficient information)
        guardrails against transferable backend skills falsely claiming AI/ML relevance
        missing experience index fallbacks
    """

    # ==================================================
    # DOMAIN SPECIFICITY DETECTION
    # ==================================================

    def _is_ai_ml_requirement(
        self,
        job_description: JobDescriptionObject,
    ) -> bool:
        """
        Detect whether the job description experience requirement targets
        Artificial Intelligence, Machine Learning, Deep Learning, Computational
        Science, Data Science, NLP, Computer Vision, or Generative AI.
        """
        ai_ml_keywords = (
            "ai",
            "ml",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "computational science",
            "data science",
            "nlp",
            "natural language processing",
            "computer vision",
            "genai",
            "generative ai",
            "large language model",
            "llm",
            "neural network",
            "pytorch",
            "tensorflow",
        )

        # Check preferred domains in experience requirements
        for requirement in job_description.experience_requirements:
            for domain in requirement.preferred_domains:
                clean_domain = domain.lower().strip()
                if any(kw in clean_domain for kw in ai_ml_keywords):
                    return True

        # Check responsibilities and required skills context
        combined_context = " ".join(
            (job_description.required_skills or [])
            + (job_description.responsibilities or [])
            + (job_description.tools_and_technologies or [])
        ).lower()

        return any(
            kw in combined_context
            for kw in (
                "computational science",
                "machine learning",
                "deep learning",
                "artificial intelligence",
                "data science",
                "generative ai",
            )
        )

    # ==================================================
    # CHECK MEANINGFUL EXPERIENCE REQUIREMENT
    # ==================================================

    def has_meaningful_experience_requirement(
        self,
        job_description: JobDescriptionObject,
    ) -> bool:
        """
        Determine whether the JD contains an actual experience requirement.

        Qwen should run when at least one of these exists:
        - minimum_years
        - maximum_years
        - preferred_domains

        This prevents Qwen from being called for fresher roles or JDs
        where experience is not specified.
        """
        for requirement in job_description.experience_requirements:
            if requirement.minimum_years is not None:
                return True
            if requirement.maximum_years is not None:
                return True
            if any(
                domain and domain.strip()
                for domain in requirement.preferred_domains
            ):
                return True

        return False

    # ==================================================
    # BUILD EXPERIENCE REQUIREMENTS
    # ==================================================

    def build_experience_requirements(
        self,
        job_description: JobDescriptionObject,
    ) -> list[dict]:
        """
        Convert structured JD experience requirements into a compact
        JSON-compatible representation.
        """
        experience_requirements = []

        for requirement in job_description.experience_requirements:
            experience_requirements.append(
                {
                    "minimum_years": requirement.minimum_years,
                    "maximum_years": requirement.maximum_years,
                    "preferred_domains": [
                        domain.strip()
                        for domain in requirement.preferred_domains
                        if domain and domain.strip()
                    ],
                }
            )

        return experience_requirements

    # ==================================================
    # BUILD RESUME EXPERIENCES
    # ==================================================

    def build_resume_experiences(
        self,
        resume: ResumeObject,
    ) -> list[dict]:
        """
        Convert candidate professional experiences into a compact representation
        for LLM evaluation. Handles both Pydantic Experience objects and dicts.
        """
        resume_experiences = []

        for index, experience in enumerate(resume.experience):
            if hasattr(experience, "role"):
                role = experience.role
                company = experience.company
                start_date = experience.start_date
                end_date = experience.end_date
                description = experience.description
            elif isinstance(experience, dict):
                role = experience.get("role")
                company = experience.get("company")
                start_date = experience.get("start_date")
                end_date = experience.get("end_date")
                description = experience.get("description")
            else:
                role = getattr(experience, "role", None)
                company = getattr(experience, "company", None)
                start_date = getattr(experience, "start_date", None)
                end_date = getattr(experience, "end_date", None)
                description = getattr(experience, "description", None)

            resume_experiences.append(
                {
                    "experience_index": index,
                    "role": role,
                    "company": company,
                    "start_date": start_date,
                    "end_date": end_date,
                    "description": description or "",
                }
            )

        return resume_experiences

    # ==================================================
    # BUILD JD CONTEXT
    # ==================================================

    def build_jd_context(
        self,
        job_description: JobDescriptionObject,
    ) -> dict:
        """
        Build additional JD context for determining experience relevance.
        """
        return {
            "required_skills": [
                skill.strip()
                for skill in job_description.required_skills
                if skill and skill.strip()
            ],
            "responsibilities": [
                resp.strip()
                for resp in job_description.responsibilities
                if resp and resp.strip()
            ],
            "tools_and_technologies": [
                tool.strip()
                for tool in job_description.tools_and_technologies
                if tool and tool.strip()
            ],
        }

    # ==================================================
    # BUILD PROMPT
    # ==================================================

    def build_prompt(
        self,
        job_description: JobDescriptionObject,
        resume: ResumeObject,
    ) -> str:
        """
        Build the prompt sent to Qwen.

        Enforces strict evidence verification, title-invariance, negative
        constraints against generic backend development for AI/ML, and explicit
        decision semantics.
        """
        experience_requirements = self.build_experience_requirements(
            job_description
        )
        jd_context = self.build_jd_context(job_description)
        resume_experiences = self.build_resume_experiences(resume)
        is_ai_ml = self._is_ai_ml_requirement(job_description)

        domain_specific_rules = ""
        if is_ai_ml:
            domain_specific_rules = """
CRITICAL NEGATIVE CONSTRAINTS FOR AI / MACHINE LEARNING / COMPUTATIONAL SCIENCE CRITERIA:
1. Generic Python development alone DOES NOT constitute AI/ML experience.
2. Generic backend frameworks (Flask, FastAPI, Django, Express, Spring Boot) DO NOT establish AI/ML experience.
3. Building REST APIs, writing CRUD operations, querying relational or NoSQL databases (SQL, PostgreSQL, MongoDB, Cosmos DB) DO NOT establish AI/ML experience.
4. Cloud hosting, virtual machines, containerization (Docker, Azure, AWS, GCP), Swagger/OpenAPI documentation, and Postman testing DO NOT establish AI/ML experience by themselves.
5. If an experience only documents generic backend web services or database integrations without actual machine learning modeling, fine-tuning, loss optimization, neural networks, or ML inference pipelines, you MUST classify it as IRRELEVANT (evidence_classification: "TRANSFERABLE_BACKEND", relevance_ratio: 0.0).
6. Transferable backend skills MUST NOT receive PARTIALLY_RELEVANT credit merely because backend engineering is transferable.
"""

        return f"""You are TalentAI's Evidence-Based Experience Relevance Judge.

Your ONLY task is to evaluate whether each candidate's professional work experience provides verifiable evidence of relevant work matching the experience requirement of the Job Description.

Evaluate ONLY professional work experiences. Do NOT evaluate education, certifications, personal projects, or general resume formatting.
Do NOT calculate years or duration. Python computes duration separately.
Do NOT invent facts, deliverables, percentages, or achievements not explicitly written in the candidate's description.

==================================================
JOB DESCRIPTION EXPERIENCE REQUIREMENT
==================================================
{json.dumps(experience_requirements, indent=2)}

==================================================
JOB DESCRIPTION CONTEXT
==================================================
Required skills:
{json.dumps(jd_context["required_skills"], indent=2)}

Responsibilities:
{json.dumps(jd_context["responsibilities"], indent=2)}

Tools and technologies:
{json.dumps(jd_context["tools_and_technologies"], indent=2)}

==================================================
CANDIDATE PROFESSIONAL EXPERIENCES
==================================================
{json.dumps(resume_experiences, indent=2)}
{domain_specific_rules}
==================================================
MANDATORY DECISION RULES & PRINCIPLES
==================================================

1. TITLE INVARIANCE (Deliverables Over Titles):
   - Judge actual responsibilities, deliverables, and technical work, NEVER the job title alone.
   - A generic title (e.g., "Software Engineer", "Consultant", "Research Intern") with genuine domain deliverables (e.g., trained convolutional neural networks or transformer models in PyTorch) is RELEVANT.
   - An impressive or domain-branded title (e.g., "AI Engineer Intern", "Machine Learning Associate") with only ordinary web development or CRUD APIs is IRRELEVANT.

2. CLASSIFICATION DEFINITIONS:

   - RELEVANT:
     Use when documented work substantively matches the JD's required professional-experience domain.
     For AI/ML: Actual model training, fine-tuning, architecture design, loss optimization, model evaluation metrics (AUC, F1, precision/recall), or data pipelines specifically for model training.
     relevance_ratio: 1.0.

   - PARTIALLY_RELEVANT:
     Use ONLY when the resume provides concrete evidence of ACTUAL domain-related work mixed with unrelated responsibilities.
     Example: Candidate developed general backend services AND deployed/integrated a genuine ML model for production inference.
     CRITICAL: Do NOT assign PARTIALLY_RELEVANT merely because backend skills are transferable. If there is zero actual domain work, it is IRRELEVANT.
     relevance_ratio: 0.5 (or the specific percentage if explicitly documented in the resume text, e.g. "40% ML").

   - IRRELEVANT:
     Use when the documented work contains no substantive domain-related deliverables.
     Generic backend development (Flask/FastAPI REST APIs, Cosmos DB, Azure hosting, Postman, Swagger) against an AI/ML requirement is IRRELEVANT.
     Completely unrelated professions (Design, Marketing, Sales) are IRRELEVANT.
     relevance_ratio: 0.0. relevant_work_summary: null.

   - AMBIGUOUS:
     Use when there is plausible connection but insufficient evidence to confirm or refute relevant deliverables.
     relevance_ratio: 0.0. relevant_work_summary: null.

   - INSUFFICIENT_INFORMATION:
     Use when the description is vague, generic, or empty (e.g., "worked on AI technologies", "assisted data team", "various tasks") with no verifiable technical deliverables.
     relevance_ratio: 0.0. relevant_work_summary: null.

3. RELEVANT WORK SUMMARY:
   - Concise, unembellished candidate excerpt of substantive domain deliverables.
   - MUST be null for IRRELEVANT, AMBIGUOUS, and INSUFFICIENT_INFORMATION.
   - Do NOT invent text.

4. EVIDENCE CLASSIFICATION:
   - "MODEL_TRAINING_OR_EVAL": Training, fine-tuning, loss optimization, validation of ML/DL models.
   - "INFERENCE_DEPLOYMENT": Serving trained models, ONNX runtime, low-latency inference endpoints.
   - "DATA_PIPELINE": Feature engineering and data pipelines specifically built for ML training/eval.
   - "TRANSFERABLE_BACKEND": Web services, REST APIs, databases, cloud hosting without ML (IRRELEVANT for AI/ML criteria).
   - "UNRELATED": Non-software or completely unrelated profession.
   - "UNSPECIFIED": Insufficient technical detail.

5. CONFIDENCE:
   - "HIGH": Direct, unambiguous evidence confirming or refuting relevance.
   - "MEDIUM": Plausible evidence with limited technical detail.
   - "LOW": High ambiguity or vague wording.

==================================================
OUTPUT FORMAT
==================================================
Return ONLY valid JSON matching the ExperienceRelevanceResult schema.
Return exactly one decision for EVERY candidate experience (experience_index 0, 1, ...).
Preserve the exact experience_index.
"""

    # ==================================================
    # DETERMINISTIC DECISION NORMALIZATION
    # ==================================================

    def normalize_decision(
        self,
        decision: ExperienceRelevanceDecision,
        candidate_experience: Experience | dict | None = None,
        is_ai_ml_criterion: bool = False,
    ) -> ExperienceRelevanceDecision:
        """
        Enforce deterministic business rules, safeguards, and schema invariants
        on each LLM relevance decision.

        Safeguards:
        - For AI/ML JDs: If classification is TRANSFERABLE_BACKEND, enforce IRRELEVANT (ratio 0.0).
        - RELEVANT: ratio 1.0.
        - PARTIALLY_RELEVANT: ratio 0.5 default, or explicit documented ratio in (0.0, 1.0).
        - IRRELEVANT / AMBIGUOUS / INSUFFICIENT_INFORMATION: ratio 0.0, summary null, domains empty.
        """
        raw_decision: ExperienceDecision = decision.decision
        classification = decision.evidence_classification
        ratio = decision.relevance_ratio
        work_summary = decision.relevant_work_summary
        matched_domains = list(decision.matched_domains or [])
        matched_context = list(decision.matched_context or [])
        confidence = decision.confidence

        # Safeguard Rule 2 & 4: Transferable backend alone must NOT receive AI/ML credit
        if is_ai_ml_criterion and classification == "TRANSFERABLE_BACKEND":
            raw_decision = "IRRELEVANT"
            work_summary = None
            matched_domains = []
            matched_context = []
            ratio = 0.0

        # Deterministic ratio & field enforcement
        if raw_decision == "RELEVANT":
            ratio = 1.0
            if work_summary and work_summary.strip():
                work_summary = work_summary.strip()
            elif candidate_experience:
                # If LLM omitted work_summary for confirmed RELEVANT role, use candidate's actual text
                desc = getattr(candidate_experience, "description", None) or (
                    candidate_experience.get("description")
                    if isinstance(candidate_experience, dict)
                    else None
                )
                if desc and desc.strip():
                    work_summary = desc.strip()
                else:
                    work_summary = None
            else:
                work_summary = None
        elif raw_decision == "PARTIALLY_RELEVANT":
            # 0.5 by default unless an explicit documented ratio was parsed in (0.0, 1.0)
            if ratio is not None and 0.0 < float(ratio) < 1.0:
                ratio = round(float(ratio), 2)
            else:
                ratio = 0.5
            if work_summary and not work_summary.strip():
                work_summary = None
        else:
            # IRRELEVANT, AMBIGUOUS, INSUFFICIENT_INFORMATION
            ratio = 0.0
            work_summary = None
            matched_domains = []
            matched_context = []

        # Clamp ratio strictly between 0.0 and 1.0
        ratio = max(0.0, min(1.0, float(ratio)))

        return ExperienceRelevanceDecision(
            experience_index=decision.experience_index,
            decision=raw_decision,
            matched_domains=matched_domains,
            matched_context=matched_context,
            reason=decision.reason or "",
            relevant_work_summary=work_summary,
            relevance_ratio=ratio,
            evidence_classification=classification,
            confidence=confidence,
        )

    # ==================================================
    # EVALUATE EXPERIENCES
    # ==================================================

    async def evaluate_experiences(
        self,
        job_description: JobDescriptionObject,
        resume: ResumeObject,
    ) -> ExperienceRelevanceResult:
        """
        Evaluate all candidate professional experiences using Qwen,
        followed by deterministic validation and normalization.

        Qwen is skipped completely when the JD does not contain a
        meaningful experience requirement or the resume has no experience entries.
        """
        # Skip if no meaningful experience requirement
        if not self.has_meaningful_experience_requirement(job_description):
            return ExperienceRelevanceResult(experience_decisions=[])

        # Skip if candidate has no experience
        if not resume.experience:
            return ExperienceRelevanceResult(experience_decisions=[])

        is_ai_ml = self._is_ai_ml_requirement(job_description)

        # Build prompt
        prompt = self.build_prompt(
            job_description=job_description,
            resume=resume,
        )

        # Call Qwen via LLMService
        response = await llm_service.generate_json(
            prompt=prompt,
            schema=ExperienceRelevanceResult,
        )

        # Robust extraction from response dictionary
        raw_decisions: list[ExperienceRelevanceDecision] = []
        if isinstance(response, dict) and "experience_decisions" in response:
            for item in response["experience_decisions"]:
                try:
                    raw_decisions.append(
                        ExperienceRelevanceDecision.model_validate(item)
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to validate ExperienceRelevanceDecision item: %s",
                        exc,
                    )
        elif isinstance(response, ExperienceRelevanceResult):
            raw_decisions = response.experience_decisions

        # Map decisions by experience_index
        decisions_by_index = {
            d.experience_index: d for d in raw_decisions
        }

        # Normalize and guarantee every index is present
        final_decisions: list[ExperienceRelevanceDecision] = []
        total_experiences = len(resume.experience)

        for index in range(total_experiences):
            cand_exp = resume.experience[index]
            if index in decisions_by_index:
                decision_item = decisions_by_index[index]
            else:
                decision_item = ExperienceRelevanceDecision(
                    experience_index=index,
                    decision="INSUFFICIENT_INFORMATION",
                    reason="Model omitted decision for this experience entry.",
                    relevance_ratio=0.0,
                    evidence_classification="UNSPECIFIED",
                    confidence="LOW",
                )

            normalized = self.normalize_decision(
                decision=decision_item,
                candidate_experience=cand_exp,
                is_ai_ml_criterion=is_ai_ml,
            )
            final_decisions.append(normalized)

        return ExperienceRelevanceResult(experience_decisions=final_decisions)


experience_llm_service = ExperienceLLMService()
