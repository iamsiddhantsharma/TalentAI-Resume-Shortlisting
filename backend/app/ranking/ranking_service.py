"""
TalentAI — Phase 6: Explainable Ranking Engine Service

Implements pure mathematical scoring functions, evidence extraction,
category applicability, dynamic weight renormalization, and candidate
ranking orchestration.
"""

import asyncio
from datetime import datetime, timezone
import logging
import math
import re
from typing import Any
import uuid

from app.database.batch_repository import batch_repository
from app.database.jd_embedding_repository import jd_embedding_repository
from app.database.jd_repository import jd_repository
from app.database.mongodb import mongodb
from app.database.ranking_job_repository import ranking_job_repository
from app.database.resume_embedding_repository import resume_embedding_repository
from app.database.resume_repository import resume_repository
from app.ranking.ranking_config import (
    BASE_WEIGHTS,
    CATEGORICAL_EXPERIENCE_SCORES,
    SEMANTIC_RETRIEVAL_THRESHOLD,
    USE_EVIDENCE_BASED_EXPERIENCE,
)
from app.ranking.ranking_schemas import (
    BatchRankingResponse,
    CandidateRankingResult,
    CandidateRankingStatus,
    CategoryApplicability,
    CategoryScoreBreakdown,
    ExperienceCriterionEvidenceItem,
    MinimumExperienceDiagnostic,
    RankingJobStatusResponse,
    SemanticRequirementEvidenceItem,
    SkillEvidenceItem,
)
from app.schemas.job_description import JobDescription
from app.schemas.job_description_object import JobDescriptionObject
from app.schemas.matching import (
    ExactMatchingResult,
    ExperienceMatchingResult,
    ResumeMatchResult,
    SemanticRetrievalResult,
)
from app.services.hybrid_matching_service import hybrid_matching_service
from app.services.ai_lifecycle_manager import ai_lifecycle_manager

logger = logging.getLogger(__name__)


class RankingEngine:
    """
    Stand-alone, explainable ranking engine.

    Responsibilities:
    1. Pure scoring functions for 4 components (Skills, Responsibilities, Tools, Experience).
    2. Dynamic category applicability determination strictly from the active JD.
    3. Proportional weight renormalization when categories do not apply.
    4. Deterministic linear normalization above the 0.65 semantic retrieval threshold.
    5. JD-defined denominator for experience relevance.
    6. Safe handling of missing evidence vs. technical service failures.
    7. Explainable component score breakdowns and candidate ranking.
    8. Asynchronous background batch ranking jobs with bounded concurrency.
    """

    def __init__(
        self,
        base_weights: dict[str, float] | None = None,
        retrieval_threshold: float = SEMANTIC_RETRIEVAL_THRESHOLD,
        experience_categorical_scores: dict[str, float] | None = None,
        max_llm_concurrency: int = 1,
        use_evidence_based_experience: bool | None = None,
    ):
        self.base_weights = (
            dict(base_weights) if base_weights is not None else dict(BASE_WEIGHTS)
        )
        self.retrieval_threshold = retrieval_threshold
        self.experience_categorical_scores = (
            dict(experience_categorical_scores)
            if experience_categorical_scores is not None
            else dict(CATEGORICAL_EXPERIENCE_SCORES)
        )
        self._llm_semaphore = asyncio.Semaphore(max_llm_concurrency)
        self._active_tasks: dict[str, asyncio.Task] = {}
        self.use_evidence_based_experience = (
            use_evidence_based_experience
            if use_evidence_based_experience is not None
            else USE_EVIDENCE_BASED_EXPERIENCE
        )


    # ==========================================================================
    # PURE NORMALIZATION HELPERS
    # ==========================================================================

    @staticmethod
    def _get_field(obj: Any, field_name: str, default: Any = None) -> Any:
        """Safely extract field from either a dict or a Pydantic model / object."""
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(field_name, default)
        return getattr(obj, field_name, default)

    @staticmethod
    def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Clamp float value into [min_val, max_val]."""
        return max(min_val, min(value, max_val))

    def normalize_similarity(
        self,
        similarity: float,
        threshold: float | None = None,
    ) -> float:
        """
        Linearly normalize raw cosine similarity above the threshold to [0.0, 1.0].

        Formula:
            normalized = clamp((similarity - threshold) / (1.0 - threshold), 0.0, 1.0)
            if similarity < threshold, normalized = 0.0
        """
        th = threshold if threshold is not None else self.retrieval_threshold
        if similarity < th:
            return 0.0
        if th >= 1.0:
            return 1.0 if similarity >= 1.0 else 0.0
        normalized = (similarity - th) / (1.0 - th)
        return self.clamp(normalized, 0.0, 1.0)

    # ==========================================================================
    # 1. CATEGORY APPLICABILITY & WEIGHT RENORMALIZATION
    # ==========================================================================

    def extract_jd_experience_criteria(
        self,
        job_description: JobDescriptionObject,
    ) -> list[str]:
        """
        Extract fixed JD-defined experience criteria (unique preferred domains).

        Preserves first-occurrence order and case-insensitive uniqueness.
        """
        criteria: list[str] = []
        seen: set[str] = set()

        for req in job_description.experience_requirements:
            for domain in req.preferred_domains:
                if domain and domain.strip():
                    cleaned = domain.strip()
                    if cleaned.lower() not in seen:
                        seen.add(cleaned.lower())
                        criteria.append(cleaned)

        return criteria

    def determine_category_applicability(
        self,
        job_description: JobDescriptionObject,
    ) -> dict[str, CategoryApplicability]:
        """
        Determine applicability strictly from the Job Description.

        Rules:
        - required_skills: applicable if len(jd.required_skills) > 0
        - responsibilities: applicable if len(jd.responsibilities) > 0
        - tools_and_technologies: applicable if len(jd.tools_and_technologies) > 0
        - experience_relevance: applicable if len(preferred_domains) > 0
        """
        experience_criteria = self.extract_jd_experience_criteria(job_description)

        return {
            "required_skills": (
                "applicable"
                if len(job_description.required_skills) > 0
                else "not_applicable"
            ),
            "responsibilities": (
                "applicable"
                if len(job_description.responsibilities) > 0
                else "not_applicable"
            ),
            "tools_and_technologies": (
                "applicable"
                if len(job_description.tools_and_technologies) > 0
                else "not_applicable"
            ),
            "experience_relevance": (
                "applicable"
                if len(experience_criteria) > 0
                else "not_applicable"
            ),
        }

    def normalize_weights(
        self,
        applicability: dict[str, CategoryApplicability],
    ) -> dict[str, float]:
        """
        Dynamically renormalize weights across applicable categories.

        Formula:
            Let A be the set of applicable categories.
            W_i = base_weight_i / sum(base_weight_j for j in A)
            If category is not applicable, W_i = 0.0.
            If no categories are applicable, all W_i = 0.0.
        """
        applicable_keys = [
            cat for cat, status in applicability.items()
            if status in ("applicable", "complete")
        ]

        total_applicable_weight = sum(
            self.base_weights.get(cat, 0.0) for cat in applicable_keys
        )

        normalized_weights: dict[str, float] = {}

        for cat in self.base_weights:
            if cat in applicable_keys and total_applicable_weight > 0.0:
                normalized_weights[cat] = (
                    self.base_weights[cat] / total_applicable_weight
                )
            else:
                normalized_weights[cat] = 0.0

        return normalized_weights

    # ==========================================================================
    # 2. COMPONENT A: REQUIRED SKILLS SCORE (0–100)
    # ==========================================================================

    def calculate_required_skills_score(
        self,
        exact_matching_data: dict[str, Any] | ExactMatchingResult | None,
        jd_required_skills: list[str],
    ) -> tuple[float | None, CategoryApplicability, int, int, list[dict[str, Any]], str | None]:
        """
        Calculate Component A score:
            K = (matched_required_skills / total_required_skills) * 100

        Returns:
            (score, status, total_criteria, qualifying_criteria, evidence, notes)
        """
        total_jd_skills = len(jd_required_skills)

        # Category Applicability check from JD
        if total_jd_skills == 0:
            return (
                None,
                "not_applicable",
                0,
                0,
                [],
                "Job Description defines no required skills.",
            )

        # Technical service failure check
        if exact_matching_data is None:
            return (
                None,
                "unavailable",
                total_jd_skills,
                0,
                [],
                "Required skills matching service result is unavailable.",
            )

        if isinstance(exact_matching_data, dict):
            err = exact_matching_data.get("error")
            stat = exact_matching_data.get("status")
            if err or stat in ("failed", "unavailable", "incomplete", "error"):
                return (
                    None,
                    "unavailable",
                    total_jd_skills,
                    0,
                    [],
                    f"Required skills matching service failure: {err or stat}",
                )
        else:
            err = getattr(exact_matching_data, "error", None)
            stat = getattr(exact_matching_data, "status", None)
            if err or stat in ("failed", "unavailable", "incomplete", "error"):
                return (
                    None,
                    "unavailable",
                    total_jd_skills,
                    0,
                    [],
                    f"Required skills matching service failure: {err or stat}",
                )

        # Extract data from model or dict
        if isinstance(exact_matching_data, ExactMatchingResult):
            matched_count = exact_matching_data.matched_required_skills
            raw_matches = exact_matching_data.matches
        else:
            matched_count = exact_matching_data.get("matched_required_skills", 0)
            raw_matches = exact_matching_data.get("matches", [])

        # Build clean explainable evidence list
        evidence_list: list[dict[str, Any]] = []
        matches_by_req: dict[str, Any] = {}
        for m in raw_matches:
            req_skill = self._get_field(m, "required_skill")
            if req_skill:
                matches_by_req[req_skill.strip().lower()] = m

        for req in jd_required_skills:
            m = matches_by_req.get(req.strip().lower())
            is_matched = False
            matched_skill = None
            evidence_type = None

            if m:
                is_matched = self._get_field(m, "matched", False)
                matched_skill = self._get_field(m, "resume_skill")
                evidence_type = self._get_field(m, "match_type")

            evidence_item = SkillEvidenceItem(
                required_skill=req,
                matched=is_matched,
                matched_resume_skill=matched_skill,
                evidence_type=evidence_type,
            )
            evidence_list.append(evidence_item.model_dump())

        # Validate count consistency with evidence
        validated_matched_count = sum(1 for e in evidence_list if e.get("matched") is True)
        note_skills: str | None = None
        if matched_count != validated_matched_count:
            logger.warning(
                "Upstream matched_required_skills (%d) disagreed with validated evidence count (%d). "
                "Reconciling to match validated evidence.",
                matched_count,
                validated_matched_count,
            )
            note_skills = (
                f"Upstream matched count ({matched_count}) reconciled to match validated evidence ({validated_matched_count})."
            )

        # Final validated matched count guarantees mathematical agreement with evidence
        final_matched_count = validated_matched_count

        # Calculate score (scale 0–100)
        # Use total_jd_skills as denominator
        score = (float(final_matched_count) / float(total_jd_skills)) * 100.0
        clamped_score = self.clamp(score, 0.0, 100.0)

        return (
            clamped_score,
            "complete",
            total_jd_skills,
            final_matched_count,
            evidence_list,
            note_skills,
        )

    # ==========================================================================
    # RETRIEVAL SECTION EXTRACTION HELPER
    # ==========================================================================

    def _extract_section_retrieval(
        self,
        retrieval_data: dict[str, Any] | SemanticRetrievalResult | None,
        section_key: str,
    ) -> tuple[list[Any] | None, str | None]:
        """
        Extract section retrieval results from dict or SemanticRetrievalResult.

        Handles dict and Pydantic paths symmetrically:
        - None or missing section: returns (None, "unavailable")
        - Top-level or section-level errors / failed statuses: returns (None, error_msg)
        - Valid section with results (even empty list): returns (results_list, None)
        """
        sec_label = section_key.replace("_", " ").capitalize()

        if retrieval_data is None:
            return None, "Semantic retrieval service result is unavailable."

        # Top-level failure checks
        if isinstance(retrieval_data, dict):
            top_err = retrieval_data.get("error")
            top_stat = retrieval_data.get("status")
            if top_err or top_stat in ("failed", "unavailable", "incomplete", "error"):
                return None, f"Semantic retrieval failure: {top_err or top_stat}"

            if section_key in retrieval_data:
                sec_obj = retrieval_data.get(section_key)
                if sec_obj is None:
                    return None, f"{sec_label} result is missing or unavailable."
                if isinstance(sec_obj, dict):
                    sec_err = sec_obj.get("error")
                    sec_stat = sec_obj.get("status")
                    if sec_err or sec_stat in ("failed", "unavailable", "incomplete", "error"):
                        return None, f"{sec_label} failed: {sec_err or sec_stat}"
                    return sec_obj.get("results", []), None
                elif hasattr(sec_obj, "results"):
                    sec_err = getattr(sec_obj, "error", None)
                    sec_stat = getattr(sec_obj, "status", None)
                    if sec_err or sec_stat in ("failed", "unavailable", "incomplete", "error"):
                        return None, f"{sec_label} failed: {sec_err or sec_stat}"
                    return sec_obj.results, None
                else:
                    return None, f"Invalid {section_key} format."
            elif "results" in retrieval_data:
                # Flat legacy format
                return retrieval_data.get("results", []), None
            else:
                return None, f"{sec_label} result is missing or unavailable."

        # Pydantic SemanticRetrievalResult
        top_err = getattr(retrieval_data, "error", None)
        top_stat = getattr(retrieval_data, "status", None)
        if top_err or top_stat in ("failed", "unavailable", "incomplete", "error"):
            return None, f"Semantic retrieval failure: {top_err or top_stat}"

        sec_obj = getattr(retrieval_data, section_key, None)
        if sec_obj is None:
            return None, f"{sec_label} result is missing or unavailable."

        sec_err = getattr(sec_obj, "error", None)
        sec_stat = getattr(sec_obj, "status", None)
        if sec_err or sec_stat in ("failed", "unavailable", "incomplete", "error"):
            return None, f"{sec_label} failed: {sec_err or sec_stat}"

        return getattr(sec_obj, "results", []), None

    # ==========================================================================
    # 3. COMPONENT B: RESPONSIBILITIES SCORE (0–100)
    # ==========================================================================

    def calculate_responsibilities_score(
        self,
        retrieval_data: dict[str, Any] | SemanticRetrievalResult | None,
        jd_responsibilities: list[str],
    ) -> tuple[float | None, CategoryApplicability, int, int, list[dict[str, Any]], str | None]:
        """
        Calculate Component B score:
            For each JD responsibility:
                Find strongest qualifying passage (maximum cosine similarity).
                norm_i = clamp((similarity - 0.65) / (1.0 - 0.65), 0, 1)
            R = 100 * (sum(norm_i) / number of JD responsibilities)

        Returns:
            (score, status, total_criteria, qualifying_criteria, evidence, notes)
        """
        total_responsibilities = len(jd_responsibilities)

        if total_responsibilities == 0:
            return (
                None,
                "not_applicable",
                0,
                0,
                [],
                "Job Description defines no responsibilities.",
            )

        results_list, err_msg = self._extract_section_retrieval(
            retrieval_data, "responsibilities_retrieval"
        )
        if err_msg is not None or results_list is None:
            return (
                None,
                "unavailable",
                total_responsibilities,
                0,
                [],
                err_msg or "Responsibilities retrieval result is unavailable.",
            )

        # Map results by requirement index and text (with and without prefix)
        results_by_index: dict[int, Any] = {}
        results_by_text: dict[str, Any] = {}
        for r in results_list:
            idx = self._get_field(r, "jd_item_index")
            txt = self._get_field(r, "jd_text")
            if idx is not None:
                results_by_index[idx] = r
            if txt:
                norm_txt = txt.strip().lower()
                results_by_text[norm_txt] = r
                for prefix in ("responsibility:", "responsibilities:"):
                    if norm_txt.startswith(prefix):
                        results_by_text[norm_txt[len(prefix):].strip()] = r

        evidence_list: list[dict[str, Any]] = []
        normalized_scores: list[float] = []
        qualifying_count = 0

        for i, resp_text in enumerate(jd_responsibilities):
            # Locate corresponding retrieval result by index or text
            clean_resp = resp_text.strip().lower()
            res = (
                results_by_index.get(i)
                or results_by_text.get(clean_resp)
                or results_by_text.get(f"responsibility: {clean_resp}")
            )
            matches: list[Any] = self._get_field(res, "matches", []) if res else []

            # Find strongest single passage for this responsibility (avoid summing duplicates)
            best_sim = 0.0
            best_passage: str | None = None
            best_section: str | None = None

            for m in matches:
                sim = self._get_field(m, "similarity", 0.0)
                if sim > best_sim:
                    best_sim = float(sim)
                    best_passage = self._get_field(m, "resume_text")
                    best_section = self._get_field(m, "resume_section")

            # Apply normalized relevance above threshold
            norm_rel = self.normalize_similarity(best_sim)
            normalized_scores.append(norm_rel)

            qualifies = norm_rel > 0.0
            if qualifies:
                qualifying_count += 1

            evidence_item = SemanticRequirementEvidenceItem(
                requirement_index=i,
                requirement_text=resp_text,
                best_matching_passage=best_passage,
                best_matching_section=best_section,
                raw_similarity=round(best_sim, 4),
                normalized_relevance=round(norm_rel, 4),
                qualifies=qualifies,
            )
            evidence_list.append(evidence_item.model_dump())

        score = 100.0 * (sum(normalized_scores) / float(total_responsibilities))
        clamped_score = self.clamp(score, 0.0, 100.0)

        note_resp = (
            "No qualifying passage found for defined responsibilities (all below 0.65 threshold)."
            if qualifying_count == 0
            else None
        )

        return (
            clamped_score,
            "complete",
            total_responsibilities,
            qualifying_count,
            evidence_list,
            note_resp,
        )

    # ==========================================================================
    # 4. COMPONENT C: TOOLS AND TECHNOLOGIES SCORE (0–100)
    # ==========================================================================

    @staticmethod
    def _check_tool_in_text(tool_text: str, text: str) -> bool:
        """
        Grounded verification that a tool is mentioned in actual candidate text.
        Handles special non-alphanumeric tools (C++, C#, .NET, Node.js),
        single-letter tools (C, R), and disambiguates common English words
        (Go, Spring, Spark, Chef, Ant).
        """
        clean = tool_text.strip().lower()
        for prefix in ("tool or technology:", "tool:", "technology:"):
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()

        if not clean:
            return False

        # 1. Ambiguous common English words require technical contextual verification
        ambiguous_patterns: dict[str, list[str]] = {
            "go": [
                r'\bgolang\b',
                r'\bgo\s+(?:language|programming|developer|engineer|code|microservices?|backend|api|services?)\b',
                r'\b(?:written|coded|developed|implemented|built|services?)\s+in\s+go\b',
                r'\b(?:python|c\+\+|c\#|java|rust|docker|kubernetes|aws|sql)[,\s/]+go\b',
                r'\bgo[,\s/]+(?:python|c\+\+|c\#|java|rust|docker|kubernetes|aws|sql)\b',
            ],
            "spring": [
                r'\bspring\s+(?:boot|framework|mvc|cloud|security|data|batch)\b',
                r'\bjava\s+spring\b',
                r'\bspring[,\s/]+(?:hibernate|java|quarkus|micronaut)\b',
                r'\b(?:hibernate|java|quarkus|micronaut)[,\s/]+spring\b',
            ],
            "spark": [
                r'\bapache\s+spark\b',
                r'\bpyspark\b',
                r'\bspark\s+(?:streaming|sql|dataframe|mllib|jobs?|clusters?|pipelines?|processing|engine)\b',
                r'\b(?:hadoop|kafka|flink|databricks|scala)[,\s/]+spark\b',
                r'\bspark[,\s/]+(?:hadoop|kafka|flink|databricks|scala)\b',
            ],
            "chef": [
                r'\bchef\s+(?:automation|recipes?|cookbooks?|infra|infrastructure|server|client)\b',
                r'\b(?:puppet|ansible|terraform|saltstack)[,\s/]+chef\b',
                r'\bchef[,\s/]+(?:puppet|ansible|terraform|saltstack)\b',
            ],
            "ant": [
                r'\bapache\s+ant\b',
                r'\bant\s+(?:build|scripts?|tool|targets?)\b',
                r'\b(?:maven|gradle|make)[,\s/]+ant\b',
                r'\bant[,\s/]+(?:maven|gradle|make)\b',
            ],
            "c": [
                r'\bc\s+(?:language|programming|code|compiler|developer|engineer)\b',
                r'\b(?:written|coded|developed|programmed)\s+in\s+c\b',
                r'\b(?:embedded|ansi)\s+c\b',
                r'\bc[,\s/]+(?:c\+\+|c\#|assembly|linux|posix|embedded)\b',
                r'\b(?:c\+\+|c\#|assembly|linux|posix|embedded)[,\s/]+c\b',
            ],
            "r": [
                r'\br\s+(?:language|programming|code|scripts?|packages?|studio|shiny)\b',
                r'\b(?:rstudio|ggplot2|tidyverse)\b',
                r'\b(?:analysis|statistics|modeling|scripts?)\s+in\s+r\b',
                r'\br[,\s/]+(?:python|sas|spss|matlab|sql)\b',
                r'\b(?:python|sas|spss|matlab|sql)[,\s/]+r\b',
            ],
        }

        if clean in ambiguous_patterns:
            return any(re.search(pat, text, re.IGNORECASE) for pat in ambiguous_patterns[clean])

        # 2. Specialized non-alphanumeric token boundaries
        if clean == "c++":
            return bool(re.search(r'(?<![a-zA-Z0-9_])c\+\+(?![a-zA-Z0-9_+])', text, re.IGNORECASE))
        if clean == "c#":
            return bool(re.search(r'(?<![a-zA-Z0-9_])c\#(?![a-zA-Z0-9_#])', text, re.IGNORECASE))
        if clean in (".net", "dotnet"):
            return bool(re.search(r'(?<![a-zA-Z0-9_@/])(?:\.net|dotnet)(?![a-zA-Z0-9_])', text, re.IGNORECASE))
        if clean in ("node.js", "nodejs", "node js"):
            return bool(re.search(r'(?<![a-zA-Z0-9_])node(?:\.|\s*)js(?![a-zA-Z0-9_])', text, re.IGNORECASE))

        # 3. Standard tools using clean alphanumeric lookaround boundary
        pattern = r'(?<![a-zA-Z0-9_])' + re.escape(clean) + r'(?![a-zA-Z0-9_])'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def calculate_tools_score(
        self,
        retrieval_data: dict[str, Any] | SemanticRetrievalResult | None,
        jd_tools: list[str],
        candidate_experiences: list[dict[str, Any]] | list[Any] | None = None,
        raw_match_result: dict[str, Any] | ResumeMatchResult | None = None,
    ) -> tuple[float | None, CategoryApplicability, int, int, list[dict[str, Any]], str | None]:
        """
        Calculate Component C score:
            For each JD tool requirement:
                Find strongest qualifying project passage.
                norm_j = clamp((similarity - 0.65) / (1.0 - 0.65), 0, 1)
            D = 100 * (sum(norm_j) / number of JD tool requirements)

        Returns:
            (score, status, total_criteria, qualifying_criteria, evidence, notes)
        """
        total_tools = len(jd_tools)

        if total_tools == 0:
            return (
                None,
                "not_applicable",
                0,
                0,
                [],
                "Job Description defines no tools and technologies requirements.",
            )

        results_list, err_msg = self._extract_section_retrieval(
            retrieval_data, "tools_and_technologies_retrieval"
        )
        if err_msg is not None or results_list is None:
            return (
                None,
                "unavailable",
                total_tools,
                0,
                [],
                err_msg or "Tools retrieval result is unavailable.",
            )

        results_by_index: dict[int, Any] = {}
        results_by_text: dict[str, Any] = {}
        found_any_in_experience = False

        for r in results_list:
            idx = self._get_field(r, "jd_item_index")
            txt = self._get_field(r, "jd_text")
            if idx is not None:
                results_by_index[idx] = r
            if txt:
                norm_txt = txt.strip().lower()
                results_by_text[norm_txt] = r
                for prefix in ("tool or technology:", "tool:", "technology:"):
                    if norm_txt.startswith(prefix):
                        results_by_text[norm_txt[len(prefix):].strip()] = r

            # Check if retrieval results contained matches from candidate experience
            for m in self._get_field(r, "matches", []):
                sec = self._get_field(m, "resume_section")
                sim = float(self._get_field(m, "similarity", 0.0))
                if sec == "experience" and sim >= self.retrieval_threshold:
                    found_any_in_experience = True

        evidence_list: list[dict[str, Any]] = []
        normalized_scores: list[float] = []
        qualifying_count = 0

        for j, tool_text in enumerate(jd_tools):
            clean_tool = tool_text.strip().lower()
            res = (
                results_by_index.get(j)
                or results_by_text.get(clean_tool)
                or results_by_text.get(f"tool or technology: {clean_tool}")
            )
            matches: list[Any] = self._get_field(res, "matches", []) if res else []

            best_sim = 0.0
            best_passage: str | None = None
            best_section: str | None = None

            for m in matches:
                sim = self._get_field(m, "similarity", 0.0)
                sec = self._get_field(m, "resume_section")
                if sec == "experience" and float(sim) >= self.retrieval_threshold:
                    found_any_in_experience = True

                # Under section routing, ONLY project passages can qualify towards Component C
                if sec in ("projects", None) or sec == "projects":
                    if sim > best_sim:
                        best_sim = float(sim)
                        best_passage = self._get_field(m, "resume_text")
                        best_section = sec or "projects"

            norm_rel = self.normalize_similarity(best_sim)
            normalized_scores.append(norm_rel)

            qualifies = norm_rel > 0.0
            if qualifies:
                qualifying_count += 1

            evidence_item = SemanticRequirementEvidenceItem(
                requirement_index=j,
                requirement_text=tool_text,
                best_matching_passage=best_passage,
                best_matching_section=best_section,
                raw_similarity=round(best_sim, 4),
                normalized_relevance=round(norm_rel, 4),
                qualifies=qualifies,
            )
            evidence_list.append(evidence_item.model_dump())

        # Inspect candidate experiences for explicit tool mentions in employment history
        if candidate_experiences:
            for exp in candidate_experiences:
                exp_text = " ".join([
                    str(self._get_field(exp, "role", "") or ""),
                    str(self._get_field(exp, "company", "") or ""),
                    str(self._get_field(exp, "description", "") or ""),
                ])
                for tool in jd_tools:
                    if self._check_tool_in_text(tool, exp_text):
                        found_any_in_experience = True
                        break
                if found_any_in_experience:
                    break

        score = 100.0 * (sum(normalized_scores) / float(total_tools))
        clamped_score = self.clamp(score, 0.0, 100.0)

        if qualifying_count == 0:
            if found_any_in_experience:
                note_tools = "Tools mentioned in employment history but not in project portfolio."
            else:
                note_tools = "No qualifying project evidence found for defined tools and technologies."
        else:
            note_tools = None

        return (
            clamped_score,
            "complete",
            total_tools,
            qualifying_count,
            evidence_list,
            note_tools,
        )

    # ==========================================================================
    # 5. COMPONENT D: PROFESSIONAL EXPERIENCE RELEVANCE SCORE (0–100)
    # ==========================================================================

    def calculate_experience_relevance_score(
        self,
        experience_matching_data: dict[str, Any] | ExperienceMatchingResult | None,
        job_description: JobDescriptionObject,
        relevance_decisions: list[dict[str, Any]] | None = None,
    ) -> tuple[float | None, CategoryApplicability, int, int, list[dict[str, Any]], str | None]:
        """
        Calculate Component D score:
            Denominator is the fixed number of JD experience criteria (unique preferred_domains).
            For each criterion c:
                Evaluate evidence across all candidate professional experiences.
                Select strongest valid evidence for each criterion.
            E = 100 * (sum of best per-criterion relevance scores / number of JD experience criteria)

        Returns:
            (score, status, total_criteria, qualifying_criteria, evidence, notes)
        """
        criteria = self.extract_jd_experience_criteria(job_description)
        total_criteria = len(criteria)

        # If JD has no experience criteria/preferred domains, mark not applicable
        if total_criteria == 0:
            return (
                None,
                "not_applicable",
                0,
                0,
                [],
                "Job Description defines no preferred experience domains or criteria.",
            )

        if experience_matching_data is None:
            return (
                None,
                "unavailable",
                total_criteria,
                0,
                [],
                "Experience matching service result is unavailable.",
            )

        # Technical service failure check
        if isinstance(experience_matching_data, dict):
            err = experience_matching_data.get("error")
            stat = experience_matching_data.get("status")
            diag_stat = experience_matching_data.get("diagnostic_status")
            if err or stat in ("failed", "unavailable", "incomplete", "error") or diag_stat in ("failed", "error"):
                return (
                    None,
                    "unavailable",
                    total_criteria,
                    0,
                    [],
                    f"Experience matching service failure: {err or stat or experience_matching_data.get('diagnostic_message') or 'service failure'}",
                )
        else:
            err = getattr(experience_matching_data, "error", None)
            stat = getattr(experience_matching_data, "status", None)
            diag_stat = getattr(experience_matching_data, "diagnostic_status", None)
            if err or stat in ("failed", "unavailable", "incomplete", "error") or diag_stat in ("failed", "error"):
                return (
                    None,
                    "unavailable",
                    total_criteria,
                    0,
                    [],
                    f"Experience matching service failure: {err or stat or getattr(experience_matching_data, 'diagnostic_message', None) or 'service failure'}",
                )

        # Extract candidate experiences
        experiences: list[Any] = []
        if isinstance(experience_matching_data, ExperienceMatchingResult):
            experiences = experience_matching_data.experiences
        elif isinstance(experience_matching_data, dict):
            experiences = experience_matching_data.get("experiences", [])

        # Index any auxiliary decisions by experience index
        decisions_by_index: dict[int, dict[str, Any]] = {}
        if relevance_decisions:
            for d in relevance_decisions:
                idx = d.get("experience_index")
                if idx is not None:
                    try:
                        decisions_by_index[int(idx)] = d
                    except (ValueError, TypeError):
                        pass

        evidence_list: list[dict[str, Any]] = []
        best_scores_per_criterion: list[float] = []
        qualifying_criteria_count = 0

        # Evaluate every JD criterion across all candidate experiences
        for crit in criteria:
            crit_lower = crit.strip().lower()
            best_score = 0.0
            supporting_role: str | None = None
            supporting_company: str | None = None
            supporting_decision: str | None = None
            supporting_reason: str | None = None
            rejection_reasons: list[str] = []

            for i, exp in enumerate(experiences):
                # Extract role, company, decision
                role = self._get_field(exp, "role")
                company = self._get_field(exp, "company")
                decision = self._get_field(exp, "decision")
                is_relevant = self._get_field(exp, "relevant", False)
                relevance_score = self._get_field(exp, "relevance_score")

                # Match auxiliary decisions using each experience record's actual experience_index
                raw_exp_idx = self._get_field(exp, "experience_index")
                exp_idx: int | None = None
                if raw_exp_idx is not None:
                    try:
                        exp_idx = int(raw_exp_idx)
                    except (ValueError, TypeError):
                        exp_idx = None

                aux: dict[str, Any] = {}
                if exp_idx is not None and exp_idx in decisions_by_index:
                    aux = decisions_by_index[exp_idx]
                elif exp_idx is None and i in decisions_by_index:
                    # Narrow fallback only if experience record has no experience_index
                    aux = decisions_by_index[i]

                # Decision / relevance overrides from auxiliary decision if present
                if decision is None and aux:
                    decision = aux.get("decision")
                if "relevant" in aux and not is_relevant:
                    is_relevant = bool(aux.get("relevant", False))

                reason = aux.get("reason") or self._get_field(exp, "reason")

                # Determine if domain evidence was provided
                domain_evidence_present = False
                matched_domains: list[str] | None = None

                # Check candidate experience item and auxiliary decision for matched_domains strictly for this experience
                if isinstance(exp, dict) and "matched_domains" in exp:
                    domain_evidence_present = True
                    matched_domains = exp.get("matched_domains") or []
                elif not isinstance(exp, dict) and hasattr(exp, "matched_domains") and (
                    (hasattr(exp, "model_fields_set") and "matched_domains" in exp.model_fields_set)
                    or getattr(exp, "matched_domains", None) is not None
                ):
                    domain_evidence_present = True
                    matched_domains = getattr(exp, "matched_domains", []) or []
                elif aux and "matched_domains" in aux:
                    domain_evidence_present = True
                    matched_domains = aux.get("matched_domains") or []

                supports_criterion = False
                candidate_criterion_score = 0.0

                if domain_evidence_present:
                    # When matched_domains is explicitly present:
                    # Award evidence ONLY if the domain is explicitly supported by that experience.
                    # An empty list ([]) or non-matching domain NEVER qualifies,
                    # even if the role has a general RELEVANT decision.
                    if matched_domains and any(crit_lower == d.strip().lower() for d in matched_domains):
                        supports_criterion = True
                    elif not reason:
                        reason = f"Experience does not explicitly match preferred domain '{crit}'."
                else:
                    # Safe backward compatibility for legacy records genuinely lacking matched_domains.
                    # Do not fabricate domain matches. Use the narrowest defensible fallback.
                    if len(criteria) == 1:
                        # With exactly 1 domain in the JD, a relevant role specifically maps to that domain.
                        if is_relevant or decision == "RELEVANT":
                            supports_criterion = True
                            if not reason:
                                reason = "Legacy record lacks domain tags; general relevance attributed to single preferred domain."
                    else:
                        # For multiple domains, do not fabricate matches across domains or guess from text keywords.
                        supports_criterion = False
                        if not reason:
                            reason = f"Legacy record lacks domain metadata; cannot attribute general relevance to multi-domain criterion '{crit}'."

                if supports_criterion:
                    if relevance_score is not None:
                        candidate_criterion_score = self.clamp(float(relevance_score), 0.0, 1.0)
                    elif decision in self.experience_categorical_scores:
                        candidate_criterion_score = self.experience_categorical_scores[decision]
                    elif is_relevant:
                        candidate_criterion_score = 1.0
                    else:
                        candidate_criterion_score = 0.0
                else:
                    # Experience does not support this domain
                    candidate_criterion_score = 0.0
                    if reason:
                        rejection_reasons.append(reason)

                if candidate_criterion_score > best_score:
                    best_score = candidate_criterion_score
                    supporting_role = role
                    supporting_company = company
                    supporting_decision = decision
                    supporting_reason = reason

            best_scores_per_criterion.append(best_score)
            qualifies = best_score > 0.0
            if qualifies:
                qualifying_criteria_count += 1
            elif not supporting_reason:
                if rejection_reasons:
                    supporting_reason = rejection_reasons[0]
                elif len(experiences) == 0:
                    supporting_reason = "No candidate professional experience listed."
                else:
                    supporting_reason = f"No candidate experience qualified for preferred domain '{crit}'."

            criterion_evidence = ExperienceCriterionEvidenceItem(
                criterion=crit,
                best_relevance_score=round(best_score, 4),
                qualifies=qualifies,
                supporting_role=supporting_role,
                supporting_company=supporting_company,
                supporting_decision=supporting_decision,
                reason=supporting_reason,
            )
            evidence_list.append(criterion_evidence.model_dump())

        # Average over the fixed JD-defined denominator
        score = 100.0 * (sum(best_scores_per_criterion) / float(total_criteria))
        clamped_score = self.clamp(score, 0.0, 100.0)

        return (
            clamped_score,
            "complete",
            total_criteria,
            qualifying_criteria_count,
            evidence_list,
            None,
        )

    # ==========================================================================
    # 5B. COMPONENT D: EVIDENCE-BASED EXPERIENCE RANKING SCORE (STAGE 5C)
    # ==========================================================================

    def calculate_evidence_based_experience_score(
        self,
        experience_matching_data: dict[str, Any] | ExperienceMatchingResult | None,
        job_description: JobDescriptionObject,
        relevance_decisions: list[dict[str, Any]] | None = None,
    ) -> tuple[float | None, CategoryApplicability, int, int, list[dict[str, Any]], str | None]:
        """
        Calculate Component D score using Stage 5B evidence-based formula:
            E = 100 * S_agg * D_global
            where:
                S_agg = sum(S_m) / M
                M = number of unique preferred domains in JD (case-insensitive deduplication)
                S_m = max calibrated similarity among eligible relevant roles supporting domain m (0.0 if unsupported)
                D_global = Phase 3 global duration factor (0.0 for missing dates, invalid dates, or G1-C unbounded target)

        Rules (Stage 5C):
        - Do not multiply by relevance ratio again.
        - Do not apply the 35% weight twice (applied during category weighting in score_candidate).
        - Preserve G1-C unbounded target behavior (D=0.0).
        - Preserve missing-date safeguards (D=0.0).
        - Zero similarity credit for IRRELEVANT, AMBIGUOUS, INSUFFICIENT_INFORMATION.

        Returns:
            (score, status, total_criteria, qualifying_criteria, evidence, notes)
        """
        criteria = self.extract_jd_experience_criteria(job_description)
        total_criteria = len(criteria)

        # If JD has no experience criteria/preferred domains, mark not applicable
        if total_criteria == 0:
            return (
                None,
                "not_applicable",
                0,
                0,
                [],
                "Job Description defines no preferred experience domains or criteria.",
            )

        if experience_matching_data is None:
            return (
                None,
                "unavailable",
                total_criteria,
                0,
                [],
                "Experience matching service result is unavailable.",
            )

        # Technical service failure check
        if isinstance(experience_matching_data, dict):
            err = experience_matching_data.get("error")
            stat = experience_matching_data.get("status")
            diag_stat = experience_matching_data.get("diagnostic_status")
            if err or stat in ("failed", "unavailable", "incomplete", "error") or diag_stat in ("failed", "error"):
                return (
                    None,
                    "unavailable",
                    total_criteria,
                    0,
                    [],
                    f"Experience matching service failure: {err or stat or experience_matching_data.get('diagnostic_message') or 'service failure'}",
                )
        else:
            err = getattr(experience_matching_data, "error", None)
            stat = getattr(experience_matching_data, "status", None)
            diag_stat = getattr(experience_matching_data, "diagnostic_status", None)
            if err or stat in ("failed", "unavailable", "incomplete", "error") or diag_stat in ("failed", "error"):
                return (
                    None,
                    "unavailable",
                    total_criteria,
                    0,
                    [],
                    f"Experience matching service failure: {err or stat or getattr(experience_matching_data, 'diagnostic_message', None) or 'service failure'}",
                )

        # Extract candidate experiences
        experiences: list[Any] = []
        if isinstance(experience_matching_data, ExperienceMatchingResult):
            experiences = experience_matching_data.experiences
        elif isinstance(experience_matching_data, dict):
            experiences = experience_matching_data.get("experiences", [])

        # Index auxiliary decisions by experience index if provided
        decisions_by_index: dict[int, dict[str, Any]] = {}
        if relevance_decisions:
            for d in relevance_decisions:
                idx = d.get("experience_index")
                if idx is not None:
                    try:
                        decisions_by_index[int(idx)] = d
                    except (ValueError, TypeError):
                        pass

        # Per-domain similarity evaluation
        evidence_list: list[dict[str, Any]] = []
        domain_max_scores: list[float] = []
        qualifying_criteria_count = 0

        for crit in criteria:
            crit_lower = crit.strip().lower()
            best_s_m = 0.0
            best_role: str | None = None
            best_company: str | None = None
            best_decision: str | None = None
            best_summary: str | None = None
            best_ratio: float = 0.0
            best_duration: float = 0.0
            supporting_reason: str | None = None
            rejection_reasons: list[str] = []

            for i, exp in enumerate(experiences):
                decision = self._get_field(exp, "decision")
                is_relevant = self._get_field(exp, "relevant", False)

                raw_exp_idx = self._get_field(exp, "experience_index")
                exp_idx: int | None = None
                if raw_exp_idx is not None:
                    try:
                        exp_idx = int(raw_exp_idx)
                    except (ValueError, TypeError):
                        exp_idx = None

                aux: dict[str, Any] = {}
                if exp_idx is not None and exp_idx in decisions_by_index:
                    aux = decisions_by_index[exp_idx]
                elif exp_idx is None and i in decisions_by_index:
                    aux = decisions_by_index[i]

                if decision is None and aux:
                    decision = aux.get("decision")
                if "relevant" in aux and not is_relevant:
                    is_relevant = bool(aux.get("relevant", False))

                norm_dec = str(decision).strip().upper() if decision and isinstance(decision, str) else None

                # Rule 10: IRRELEVANT, AMBIGUOUS, INSUFFICIENT_INFORMATION receive strictly zero credit
                if norm_dec in ("IRRELEVANT", "AMBIGUOUS", "INSUFFICIENT_INFORMATION") or not is_relevant:
                    rejection_reasons.append(
                        f"Role '{self._get_field(exp, 'role')}' classified as {norm_dec or 'non-relevant'}."
                    )
                    continue

                # Check matched domains for this experience
                matched_domains: list[str] = []
                if isinstance(exp, dict) and "matched_domains" in exp:
                    matched_domains = exp.get("matched_domains") or []
                elif not isinstance(exp, dict) and hasattr(exp, "matched_domains"):
                    matched_domains = getattr(exp, "matched_domains", []) or []
                elif aux and "matched_domains" in aux:
                    matched_domains = aux.get("matched_domains") or []

                # Clean domain matches
                matched_lower = {str(d).strip().lower() for d in matched_domains if d}

                supports_criterion = False
                if matched_lower:
                    supports_criterion = crit_lower in matched_lower
                elif total_criteria == 1:
                    # Legacy fallback: single domain JD maps general relevance to that domain
                    supports_criterion = True
                else:
                    supports_criterion = False

                if not supports_criterion:
                    continue

                # Extract calibrated similarity for this role
                # Rule 7: calibrated_similarity is NOT multiplied by relevance_ratio!
                raw_cal_sim = self._get_field(exp, "calibrated_similarity")
                if raw_cal_sim is None:
                    raw_cal_sim = self._get_field(exp, "semantic_similarity", 0.0)

                cal_sim = 0.0
                if raw_cal_sim is not None:
                    try:
                        parsed_sim = float(raw_cal_sim)
                        if math.isfinite(parsed_sim):
                            cal_sim = max(0.0, min(1.0, parsed_sim))
                    except (ValueError, TypeError):
                        cal_sim = 0.0

                role_ratio = float(self._get_field(exp, "relevance_ratio", 0.0) or 0.0)
                role_dur = float(self._get_field(exp, "relevant_duration_years", 0.0) or 0.0)
                summary = self._get_field(exp, "relevant_work_summary") or aux.get("relevant_work_summary")

                # Track maximum calibrated similarity for this domain
                if cal_sim > best_s_m:
                    best_s_m = cal_sim
                    best_role = self._get_field(exp, "role")
                    best_company = self._get_field(exp, "company")
                    best_decision = norm_dec
                    best_summary = summary
                    best_ratio = role_ratio
                    best_duration = role_dur
                    supporting_reason = f"Calibrated semantic similarity: {round(best_s_m, 4)} from role '{best_role}'."

            domain_max_scores.append(best_s_m)
            qualifies = best_s_m > 0.0
            if qualifies:
                qualifying_criteria_count += 1
            else:
                if len(experiences) == 0:
                    supporting_reason = "No candidate professional experience listed."
                elif rejection_reasons:
                    supporting_reason = rejection_reasons[0]
                else:
                    supporting_reason = f"No candidate experience qualified for preferred domain '{crit}'."

            criterion_evidence = ExperienceCriterionEvidenceItem(
                criterion=crit,
                best_relevance_score=round(best_s_m, 4),
                qualifies=qualifies,
                supporting_role=best_role,
                supporting_company=best_company,
                supporting_decision=best_decision,
                reason=supporting_reason,
                relevance_ratio=round(best_ratio, 2),
                calibrated_similarity=round(best_s_m, 4),
                relevant_duration_years=round(best_duration, 2),
                relevant_work_summary=best_summary,
                confidence=self._get_field(experiences[0] if experiences else None, "confidence"),
            )
            evidence_list.append(criterion_evidence.model_dump())

        # Aggregate similarity: S_agg = sum(S_m) / M
        s_agg = sum(domain_max_scores) / float(total_criteria)
        s_agg_clamped = self.clamp(s_agg, 0.0, 1.0)

        # Global duration factor: D_global
        raw_d = self._get_field(experience_matching_data, "duration_factor", 0.0)
        d_global = 0.0
        if raw_d is not None:
            try:
                parsed_d = float(raw_d)
                if math.isfinite(parsed_d):
                    d_global = self.clamp(parsed_d, 0.0, 1.0)
            except (ValueError, TypeError):
                d_global = 0.0

        # Component D score: E = 100 * S_agg * D_global
        score_e = 100.0 * s_agg_clamped * d_global
        clamped_score = self.clamp(score_e, 0.0, 100.0)

        diag_status = self._get_field(experience_matching_data, "diagnostic_status")
        note = (
            f"Evidence-based experience score E = 100 * S_agg ({s_agg_clamped:.4f}) * D_global ({d_global:.4f}) = {clamped_score:.2f}. "
            f"Scoring method: evidence_based. Diagnostic status: {diag_status or 'ok'}."
        )

        return (
            clamped_score,
            "complete",
            total_criteria,
            qualifying_criteria_count,
            evidence_list,
            note,
        )

    # ==========================================================================
    # 6. OVERALL CANDIDATE SCORING CORE (DETERMINISTIC & TRANSPARENT)
    # ==========================================================================

    def score_candidate(
        self,
        match_result: ResumeMatchResult | dict[str, Any],
        job_description: JobDescriptionObject,
        relevance_decisions: list[dict[str, Any]] | None = None,
        use_evidence_based_experience: bool | None = None,
    ) -> CandidateRankingResult:
        """
        Compute an explainable ranking result for a single candidate.

        Calculates all 4 component scores, applies applicability rules,
        renormalizes weights, and calculates the overall score.
        """
        # Extract identifiers
        if isinstance(match_result, ResumeMatchResult):
            upload_id = match_result.upload_id
            filename = match_result.filename
            jd_id = match_result.jd_id
            exact_data = match_result.exact_matching
            retrieval_data = match_result.semantic_retrieval
            exp_data = match_result.experience_matching
        else:
            upload_id = match_result.get("upload_id", "")
            filename = match_result.get("filename", "")
            jd_id = match_result.get("jd_id", "")
            exact_data = match_result.get("exact_matching")
            retrieval_data = match_result.get("semantic_retrieval")
            exp_data = match_result.get("experience_matching")

        warnings: list[str] = []
        errors: list[str] = []

        # ----------------------------------------------------------------------
        # 1. Determine Initial Applicability from JD
        # ----------------------------------------------------------------------
        jd_applicability = self.determine_category_applicability(job_description)

        # ----------------------------------------------------------------------
        # 2. Evaluate Component Scores
        # ----------------------------------------------------------------------
        # A. Required skills
        score_skills, status_skills, total_skills, qual_skills, evid_skills, note_skills = (
            self.calculate_required_skills_score(
                exact_matching_data=exact_data,
                jd_required_skills=job_description.required_skills,
            )
        )

        # B. Responsibilities
        score_resp, status_resp, total_resp, qual_resp, evid_resp, note_resp = (
            self.calculate_responsibilities_score(
                retrieval_data=retrieval_data,
                jd_responsibilities=job_description.responsibilities,
            )
        )

        # Extract candidate experiences if available
        candidate_experiences = None
        if exp_data:
            if isinstance(exp_data, ExperienceMatchingResult):
                candidate_experiences = exp_data.experiences
            elif isinstance(exp_data, dict):
                candidate_experiences = exp_data.get("experiences", [])

        # C. Tools and technologies
        score_tools, status_tools, total_tools, qual_tools, evid_tools, note_tools = (
            self.calculate_tools_score(
                retrieval_data=retrieval_data,
                jd_tools=job_description.tools_and_technologies,
                candidate_experiences=candidate_experiences,
                raw_match_result=match_result,
            )
        )

        # D. Experience relevance (Feature-flag protected: Stage 5C evidence-based vs legacy)
        active_use_evidence = (
            use_evidence_based_experience
            if use_evidence_based_experience is not None
            else self.use_evidence_based_experience
        )

        if active_use_evidence:
            score_exp, status_exp, total_exp, qual_exp, evid_exp, note_exp = (
                self.calculate_evidence_based_experience_score(
                    experience_matching_data=exp_data,
                    job_description=job_description,
                    relevance_decisions=relevance_decisions,
                )
            )
        else:
            score_exp, status_exp, total_exp, qual_exp, evid_exp, note_exp = (
                self.calculate_experience_relevance_score(
                    experience_matching_data=exp_data,
                    job_description=job_description,
                    relevance_decisions=relevance_decisions,
                )
            )

        # Collect evaluated statuses
        category_statuses: dict[str, CategoryApplicability] = {
            "required_skills": status_skills,
            "responsibilities": status_resp,
            "tools_and_technologies": status_tools,
            "experience_relevance": status_exp,
        }

        # Check for technical service failures
        for cat, stat in category_statuses.items():
            if stat == "unavailable":
                errors.append(f"Category '{cat}' is technically unavailable due to service failure.")

        # ----------------------------------------------------------------------
        # 3. Dynamic Weight Renormalization
        # ----------------------------------------------------------------------
        normalized_weights = self.normalize_weights(category_statuses)

        # ----------------------------------------------------------------------
        # 4. Final Weighted Summation & Breakdown Assembly
        # ----------------------------------------------------------------------
        component_scores: dict[str, float | None] = {
            "required_skills": round(score_skills, 2) if score_skills is not None else None,
            "responsibilities": round(score_resp, 2) if score_resp is not None else None,
            "tools_and_technologies": round(score_tools, 2) if score_tools is not None else None,
            "experience_relevance": round(score_exp, 2) if score_exp is not None else None,
        }

        breakdown: dict[str, CategoryScoreBreakdown] = {}

        raw_category_params = [
            ("required_skills", status_skills, score_skills, total_skills, qual_skills, evid_skills, note_skills),
            ("responsibilities", status_resp, score_resp, total_resp, qual_resp, evid_resp, note_resp),
            ("tools_and_technologies", status_tools, score_tools, total_tools, qual_tools, evid_tools, note_tools),
            ("experience_relevance", status_exp, score_exp, total_exp, qual_exp, evid_exp, note_exp),
        ]

        jd_has_requirements = any(s == "applicable" for s in jd_applicability.values())
        has_unavailable = any(
            stat == "unavailable"
            for cat, stat in category_statuses.items()
            if jd_applicability.get(cat) == "applicable"
        )

        final_score: float | None = None
        status: CandidateRankingStatus = "complete"

        if not jd_has_requirements:
            status = "no_scorable_requirements"
            warnings.append("Job description contains no scorable requirements across any category.")
        elif has_unavailable:
            status = "incomplete"
            warnings.append("Candidate evaluation is incomplete because one or more applicable categories failed.")
        else:
            # All applicable categories successfully computed
            weighted_sum = 0.0
            for cat, stat, sc, tot, qual, evid, note in raw_category_params:
                w_norm = normalized_weights.get(cat, 0.0)
                if sc is not None and w_norm > 0.0:
                    weighted_sum += w_norm * sc

            final_score = round(self.clamp(weighted_sum, 0.0, 100.0), 2)
            status = "complete"

        # Build detailed category breakdowns
        for cat, stat, sc, tot, qual, evid, note in raw_category_params:
            w_orig = self.base_weights.get(cat, 0.0)
            w_norm = normalized_weights.get(cat, 0.0)
            weighted_contrib = (
                round(w_norm * sc, 4)
                if (sc is not None and w_norm > 0.0 and status == "complete")
                else None
            )

            breakdown[cat] = CategoryScoreBreakdown(
                category=cat,
                status=stat,
                score=round(sc, 2) if sc is not None else None,
                original_weight=w_orig,
                normalized_weight=round(w_norm, 6),
                weighted_contribution=weighted_contrib,
                total_criteria_count=tot,
                qualifying_criteria_count=qual,
                evidence=evid,
                notes=note,
            )

        # ----------------------------------------------------------------------
        # 5. Extract Minimum Experience Diagnostics
        # ----------------------------------------------------------------------
        exp_diag = MinimumExperienceDiagnostic()
        if exp_data:
            if isinstance(exp_data, ExperienceMatchingResult):
                exp_diag = MinimumExperienceDiagnostic(
                    minimum_years=exp_data.minimum_years,
                    maximum_years=exp_data.maximum_years,
                    relevant_duration_years=exp_data.relevant_duration_years,
                    minimum_duration_satisfied=exp_data.minimum_duration_satisfied,
                    maximum_duration_exceeded=exp_data.maximum_duration_exceeded,
                    diagnostic_status=exp_data.diagnostic_status,
                    diagnostic_message=exp_data.diagnostic_message,
                    duration_factor=getattr(exp_data, "duration_factor", 0.0) or 0.0,
                    saturation_target_years=getattr(exp_data, "saturation_target_years", None),
                    range_status=getattr(exp_data, "range_status", None),
                )
            elif isinstance(exp_data, dict):
                exp_diag = MinimumExperienceDiagnostic(
                    minimum_years=exp_data.get("minimum_years"),
                    maximum_years=exp_data.get("maximum_years"),
                    relevant_duration_years=exp_data.get("relevant_duration_years", 0.0),
                    minimum_duration_satisfied=exp_data.get("minimum_duration_satisfied", True),
                    maximum_duration_exceeded=exp_data.get("maximum_duration_exceeded", False),
                    diagnostic_status=exp_data.get("diagnostic_status"),
                    diagnostic_message=exp_data.get("diagnostic_message"),
                    duration_factor=float(exp_data.get("duration_factor", 0.0) or 0.0),
                    saturation_target_years=exp_data.get("saturation_target_years"),
                    range_status=exp_data.get("range_status"),
                )

        if exp_diag.diagnostic_status in (
            "missing_dates",
            "unparseable_dates",
            "ambiguous_dates",
            "dates_missing_or_unparseable",
            "invalid_date_range",
        ):
            warnings.append(
                f"Experience diagnostic: {exp_diag.diagnostic_message or exp_diag.diagnostic_status}"
            )

        return CandidateRankingResult(
            upload_id=upload_id,
            filename=filename,
            jd_id=jd_id,
            rank=None,
            status=status,
            final_score=final_score,
            component_scores=component_scores,
            breakdown=breakdown,
            experience_diagnostic=exp_diag,
            warnings=warnings,
            errors=errors,
        )

    # ==========================================================================
    # 7. MULTIPLE CANDIDATES RANKING & TIE-HANDLING
    # ==========================================================================

    def rank_candidates(
        self,
        scored_candidates: list[CandidateRankingResult],
    ) -> tuple[list[CandidateRankingResult], list[CandidateRankingResult]]:
        """
        Sort and rank completed candidates while separating unranked/incomplete ones.

        Sorting Rules:
        1. Candidates with status == 'complete' are ranked by final_score descending.
        2. Tie-handling: Identical scores receive consecutive or tied ranks deterministically.
           Stable identifier (filename, upload_id) is used as presentation tie-breaker only.
        3. Incomplete, failed, or unranked candidates are separated and NEVER assigned 0.0.
        """
        completed: list[CandidateRankingResult] = []
        unranked: list[CandidateRankingResult] = []

        for candidate in scored_candidates:
            if candidate.status == "complete" and candidate.final_score is not None:
                completed.append(candidate)
            else:
                c_copy = candidate.model_copy(update={"rank": None})
                unranked.append(c_copy)

        # Deterministic sorting: final_score descending, then filename ascending for stability
        completed.sort(
            key=lambda c: (-c.final_score if c.final_score is not None else 0.0, c.filename, c.upload_id)
        )

        # Assign 1-indexed ranks
        ranked: list[CandidateRankingResult] = []
        for i, cand in enumerate(completed, start=1):
            ranked_cand = cand.model_copy(update={"rank": i})
            ranked.append(ranked_cand)

        return ranked, unranked

    # ==========================================================================
    # 8. DATABASE & HYBRID SERVICE ORCHESTRATION METHODS
    # ==========================================================================

    async def get_active_jd_and_object(
        self,
        jd_id: str | None = None,
    ) -> tuple[str, JobDescriptionObject]:
        """
        Resolve active Job Description and validate structured data.
        """
        if jd_id:
            jd_doc = await jd_repository.get(jd_id)
            if not jd_doc:
                raise ValueError(f"Job description '{jd_id}' not found.")
        else:
            active_jd = await jd_repository.get_active()
            if not active_jd:
                raise ValueError("No active job description found.")
            jd_id = active_jd.get("jd_id") or active_jd.get("_id")
            jd_doc = active_jd

        raw_struct = jd_doc.get("structured_data")
        if not raw_struct:
            raise ValueError(f"Job description '{jd_id}' does not contain structured data.")

        if isinstance(raw_struct, JobDescriptionObject):
            jd_object = raw_struct
        else:
            try:
                jd_object = JobDescriptionObject.model_validate(raw_struct)
            except Exception as exc:
                raise ValueError(f"Invalid structured data in JD '{jd_id}': {exc}") from exc

        return jd_id, jd_object

    async def rank_resume(
        self,
        upload_id: str,
        filename: str,
        jd_id: str | None = None,
        use_evidence_based_experience: bool | None = None,
    ) -> CandidateRankingResult:
        """
        Score and explain a single candidate against the active Job Description.
        """
        resolved_jd_id, jd_object = await self.get_active_jd_and_object(jd_id)

        # Obtain match result using existing hybrid matching pipeline
        raw_match = await hybrid_matching_service.match_resume(
            jd_id=resolved_jd_id,
            upload_id=upload_id,
            filename=filename,
        )

        match_model = ResumeMatchResult.model_validate(raw_match)
        scored = self.score_candidate(
            match_result=match_model,
            job_description=jd_object,
            use_evidence_based_experience=use_evidence_based_experience,
        )

        # Single resume ranking sets rank=1 if complete
        if scored.status == "complete":
            return scored.model_copy(update={"rank": 1})
        return scored

    async def rank_batch(
        self,
        upload_id: str | None = None,
        jd_id: str | None = None,
        limit: int | None = None,
        skip: int = 0,
        use_evidence_based_experience: bool | None = None,
    ) -> tuple[str, str, int, list[CandidateRankingResult], list[CandidateRankingResult], bool]:
        """
        Score and rank all eligible completed candidates from the active batch.

        Enforces batch isolation: only completed candidates belonging to the
        active recruitment batch are ranked.
        """
        resolved_jd_id, jd_object = await self.get_active_jd_and_object(jd_id)

        # Verify active batch
        active_batch = await batch_repository.get_active()
        if not active_batch:
            raise ValueError("No active recruitment batch found. Please upload and activate a batch.")

        active_batch_id = active_batch.get("batch_id") or active_batch.get("_id")

        if upload_id and upload_id != active_batch_id:
            raise ValueError(
                f"Specified batch '{upload_id}' is not the active recruitment batch ('{active_batch_id}')."
            )

        target_batch_id = active_batch_id

        # Query completed resumes strictly from active batch in MongoDB
        db = mongodb.get_database()
        resumes_collection = db.get("resumes") if isinstance(db, dict) else db["resumes"]

        query: dict[str, Any] = {
            "upload_id": target_batch_id,
            "status": "completed",
            "resume_data": {"$ne": None},
        }

        total_eligible = await resumes_collection.count_documents(query)

        cursor = (
            resumes_collection.find(query, projection={"upload_id": 1, "filename": 1})
            .skip(skip)
        )
        if limit is not None and limit > 0:
            cursor = cursor.limit(limit)
            eligible_docs = await cursor.to_list(length=limit)
            has_more = (skip + len(eligible_docs)) < total_eligible
        else:
            eligible_docs = await cursor.to_list(length=None)
            has_more = False

        scored_candidates: list[CandidateRankingResult] = []

        # Preload JD embeddings once for the entire batch to eliminate redundant DB reads
        jd_emb_doc = await jd_embedding_repository.get_by_jd_id(resolved_jd_id)
        jd_embeddings = jd_emb_doc.get("embeddings", []) if jd_emb_doc else []

        for doc in eligible_docs:
            u_id = doc.get("upload_id")
            fname = doc.get("filename")
            if not u_id or not fname:
                continue

            try:
                # Check stored embeddings exist
                res_emb = await resume_embedding_repository.get(upload_id=u_id, filename=fname)
                if not res_emb or not res_emb.get("embeddings"):
                    raise ValueError(f"Stored embeddings not found for resume '{fname}'.")

                raw_match = await hybrid_matching_service.match_resume(
                    jd_id=resolved_jd_id,
                    upload_id=u_id,
                    filename=fname,
                    preloaded_jd=jd_object,
                    preloaded_jd_embeddings=jd_embeddings,
                )
                match_model = ResumeMatchResult.model_validate(raw_match)
                scored = self.score_candidate(
                    match_result=match_model,
                    job_description=jd_object,
                    use_evidence_based_experience=use_evidence_based_experience,
                )
                scored_candidates.append(scored)

            except Exception as exc:
                logger.exception("Error scoring candidate %s:%s", u_id, fname)
                failed_res = CandidateRankingResult(
                    upload_id=u_id,
                    filename=fname,
                    jd_id=resolved_jd_id,
                    rank=None,
                    status="incomplete",
                    final_score=None,
                    component_scores={},
                    breakdown={},
                    experience_diagnostic=MinimumExperienceDiagnostic(),
                    warnings=[],
                    errors=[str(exc)],
                )
                scored_candidates.append(failed_res)

        ranked, unranked = self.rank_candidates(scored_candidates)

        return (
            resolved_jd_id,
            target_batch_id,
            total_eligible,
            ranked,
            unranked,
            has_more,
        )

    # ==========================================================================
    # 9. ASYNCHRONOUS BACKGROUND JOB ORCHESTRATION
    # ==========================================================================

    async def create_and_start_ranking_job(
        self,
        upload_id: str | None = None,
        jd_id: str | None = None,
        limit: int | None = None,
        skip: int = 0,
        use_evidence_based_experience: bool | None = None,
    ) -> dict[str, Any]:
        """
        Validate active state, create an asynchronous ranking job document,
        and schedule background execution without blocking the HTTP caller.
        """
        resolved_jd_id, jd_object = await self.get_active_jd_and_object(jd_id)

        # Verify active JD embeddings exist
        jd_emb_doc = await jd_embedding_repository.get_by_jd_id(resolved_jd_id)
        if not jd_emb_doc or not jd_emb_doc.get("embeddings"):
            raise ValueError(
                f"Embeddings not found for active job description '{resolved_jd_id}'. Please generate JD embeddings."
            )

        # Verify active batch
        active_batch = await batch_repository.get_active()
        if not active_batch:
            raise ValueError("No active recruitment batch found. Please upload and activate a batch.")

        active_batch_id = active_batch.get("batch_id") or active_batch.get("_id")
        if upload_id and upload_id != active_batch_id:
            raise ValueError(
                f"Specified batch '{upload_id}' is not the active recruitment batch ('{active_batch_id}')."
            )

        if active_batch.get("status") in ["cancelled", "expired"]:
            raise ValueError(
                f"Active batch '{active_batch_id}' has status '{active_batch.get('status')}' and cannot be ranked."
            )

        target_batch_id = active_batch_id

        # Query completed resumes strictly from active batch in MongoDB
        db = mongodb.get_database()
        resumes_collection = db.get("resumes") if isinstance(db, dict) else db["resumes"]

        query: dict[str, Any] = {
            "upload_id": target_batch_id,
            "status": "completed",
            "resume_data": {"$ne": None},
        }

        total_eligible = await resumes_collection.count_documents(query)

        job_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        job_doc = {
            "job_id": job_id,
            "status": "queued",
            "batch_id": target_batch_id,
            "jd_id": resolved_jd_id,
            "total_eligible": total_eligible,
            "completed_count": 0,
            "failed_count": 0,
            "progress_percentage": 0.0,
            "created_at": created_at,
            "started_at": None,
            "finished_at": None,
            "error": None,
            "result": None,
        }

        await ranking_job_repository.create_job(job_doc)
        await ai_lifecycle_manager.register_queued_job(job_id)

        task = asyncio.create_task(
            self.execute_ranking_job(
                job_id=job_id,
                upload_id=target_batch_id,
                jd_id=resolved_jd_id,
                limit=limit,
                skip=skip,
                use_evidence_based_experience=use_evidence_based_experience,
            )
        )
        self._active_tasks[job_id] = task
        task.add_done_callback(lambda t: self._active_tasks.pop(job_id, None))

        return job_doc

    async def execute_ranking_job(
        self,
        job_id: str,
        upload_id: str,
        jd_id: str,
        limit: int | None = None,
        skip: int = 0,
        use_evidence_based_experience: bool | None = None,
    ) -> None:
        """
        Execute candidate ranking in the background with bounded concurrency,
        progress reporting, and isolated error handling.
        """
        try:
            await ai_lifecycle_manager.acquire_ai_service(job_id, context="ranking_execution")
            started_at = datetime.now(timezone.utc).isoformat()
            await ranking_job_repository.update_job(
                job_id,
                {"status": "processing", "started_at": started_at},
            )

            # Preload JD and embeddings once for the entire batch
            resolved_jd_id, jd_object = await self.get_active_jd_and_object(jd_id)
            jd_emb_doc = await jd_embedding_repository.get_by_jd_id(resolved_jd_id)
            jd_embeddings = jd_emb_doc.get("embeddings", []) if jd_emb_doc else []

            db = mongodb.get_database()
            resumes_collection = db.get("resumes") if isinstance(db, dict) else db["resumes"]

            query: dict[str, Any] = {
                "upload_id": upload_id,
                "status": "completed",
                "resume_data": {"$ne": None},
            }

            total_eligible = await resumes_collection.count_documents(query)

            cursor = (
                resumes_collection.find(query, projection={"upload_id": 1, "filename": 1})
                .skip(skip)
            )
            if limit is not None and limit > 0:
                cursor = cursor.limit(limit)
                eligible_docs = await cursor.to_list(length=limit)
                has_more = (skip + len(eligible_docs)) < total_eligible
            else:
                eligible_docs = await cursor.to_list(length=None)
                has_more = False

            scored_candidates: list[CandidateRankingResult] = []
            processed_count = 0
            failed_count = 0
            seen_filenames: set[str] = set()

            for doc in eligible_docs:
                u_id = doc.get("upload_id")
                fname = doc.get("filename")
                if not u_id or not fname:
                    continue

                if fname in seen_filenames:
                    continue
                seen_filenames.add(fname)

                try:
                    res_emb = await resume_embedding_repository.get(upload_id=u_id, filename=fname)
                    if not res_emb or not res_emb.get("embeddings"):
                        raise ValueError(f"Stored embeddings not found for resume '{fname}'.")

                    # Enforce single-slot LLM concurrency limit (RTX 4060 hardware bound)
                    async with self._llm_semaphore:
                        raw_match = await hybrid_matching_service.match_resume(
                            jd_id=resolved_jd_id,
                            upload_id=u_id,
                            filename=fname,
                            preloaded_jd=jd_object,
                            preloaded_jd_embeddings=jd_embeddings,
                        )
                        match_model = ResumeMatchResult.model_validate(raw_match)
                        scored = self.score_candidate(
                            match_result=match_model,
                            job_description=jd_object,
                            use_evidence_based_experience=use_evidence_based_experience,
                        )

                    scored_candidates.append(scored)
                    if scored.status != "complete":
                        failed_count += 1

                except Exception as exc:
                    logger.exception("Error scoring candidate %s:%s in job %s", u_id, fname, job_id)
                    failed_res = CandidateRankingResult(
                        upload_id=u_id,
                        filename=fname,
                        jd_id=resolved_jd_id,
                        rank=None,
                        status="incomplete",
                        final_score=None,
                        component_scores={},
                        breakdown={},
                        experience_diagnostic=MinimumExperienceDiagnostic(),
                        warnings=[],
                        errors=[str(exc)],
                    )
                    scored_candidates.append(failed_res)
                    failed_count += 1

                processed_count += 1
                progress_pct = (
                    round((processed_count / total_eligible) * 100.0, 1)
                    if total_eligible > 0
                    else 100.0
                )
                await ranking_job_repository.update_job(
                    job_id,
                    {
                        "completed_count": processed_count,
                        "failed_count": failed_count,
                        "progress_percentage": progress_pct,
                    },
                )

            # Rank candidates
            ranked, unranked = self.rank_candidates(scored_candidates)

            batch_response = BatchRankingResponse(
                jd_id=resolved_jd_id,
                active_batch_id=upload_id,
                total_eligible=total_eligible,
                ranked_count=len(ranked),
                unranked_count=len(unranked),
                limit=limit,
                skip=skip,
                has_more=has_more,
                ranked_candidates=ranked,
                unranked_candidates=unranked,
            )

            finished_at = datetime.now(timezone.utc).isoformat()
            await ranking_job_repository.update_job(
                job_id,
                {
                    "status": "completed",
                    "completed_count": processed_count,
                    "failed_count": failed_count,
                    "progress_percentage": 100.0,
                    "finished_at": finished_at,
                    "result": batch_response.model_dump(),
                },
            )

        except asyncio.CancelledError:
            logger.warning("Ranking job %s was cancelled.", job_id)
            finished_at = datetime.now(timezone.utc).isoformat()
            await ranking_job_repository.update_job(
                job_id,
                {
                    "status": "interrupted",
                    "finished_at": finished_at,
                    "error": "Job execution was cancelled.",
                },
            )
            raise
        except Exception as exc:
            logger.exception("Ranking job %s encountered fatal failure: %s", job_id, exc)
            finished_at = datetime.now(timezone.utc).isoformat()
            sanitized_error = "Ranking job failed due to an unexpected server error."
            if isinstance(exc, ValueError):
                sanitized_error = str(exc)
            await ranking_job_repository.update_job(
                job_id,
                {
                    "status": "failed",
                    "finished_at": finished_at,
                    "error": sanitized_error,
                },
            )
        finally:
            await ai_lifecycle_manager.release_ai_service(job_id)

    async def cancel_all_jobs(self) -> None:
        """
        Cancel all currently running background ranking tasks cleanly.
        """
        for job_id, task in list(self._active_tasks.items()):
            if not task.done():
                task.cancel()


# Global singleton instance
ranking_engine = RankingEngine()

