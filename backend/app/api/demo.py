"""
TalentAI — Milestone 1: Isolated Synthetic Demo API Router

Provides safe, in-memory endpoints for demonstrating the TalentAI ranking engine
using 100% synthetic fixtures without accessing real resumes, MongoDB collections,
the active production batch, or Ollama extraction.

Safety & Governance Invariants:
1. Purely in-memory operations over pre-computed synthetic fixtures.
2. Zero reads/writes to MongoDB database `talent_ai` or collections.
3. Protected batch `07281a64-46cf-46b4-a5c1-a0d46b13e7b2` is never accessed or modified.
4. Feature flag `USE_EVIDENCE_BASED_EXPERIENCE` remains False in production;
   Evidence vs. Legacy scoring is evaluated in-memory per request.
5. All returned objects are explicitly tagged with `is_synthetic_demo: True`.
6. Test-only fixtures are loaded lazily on demand so production startup never fails
   when tests and pilot fixtures are excluded from container deployments.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.ranking.ranking_service import RankingEngine
from app.schemas.job_description_object import JobDescriptionObject

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/demo",
    tags=["Synthetic Demo Sandbox"],
)

# Friendly display titles for each synthetic Job Description
PRESET_TITLES: dict[str, str] = {
    "JD-BROAD-01": "Principal Distributed Storage Engineer",
    "JD-BROAD-02": "Senior Event-Driven Python Architect",
    "JD-BROAD-03": "Staff Full-Stack & Web Platform Engineer",
    "JD-BROAD-04": "Lead iOS / Swift Mobile Architect",
    "JD-BROAD-05": "Principal LLM Inference & Serving Engineer",
    "JD-BROAD-06": "Senior Streaming Lakehouse Data Architect",
    "JD-BROAD-07": "Lead SRE & Telemetry Platform Architect",
    "JD-BROAD-08": "Principal Multi-Cloud Infrastructure Engineer",
    "JD-BROAD-09": "Senior Cloud Security & DevSecOps Engineer",
    "JD-BROAD-10": "Real-Time Embedded Systems Firmware Engineer",
    "JD-BROAD-11": "Senior SDET & Test Automation Architect",
    "JD-BROAD-12": "VP of Engineering & Technical Delivery Leader",
}

# Module-level cache for lazy fixture resolution
_fixtures_module: Any = None


def _get_fixtures() -> Any:
    """
    Lazily import the broad synthetic pilot fixtures on first request.

    Keeps test-only fixtures and paths out of production application startup.
    When running in test, development, or pilot environments where tests/pilot/fixtures_broad.py
    exists, dynamically resolves and caches the module. If fixtures are not installed
    (e.g., lean production container), raises a clear HTTP 503 error instead of crashing.
    """
    global _fixtures_module
    if _fixtures_module is not None:
        return _fixtures_module

    # 1. Check if fixtures_broad is already importable on the existing sys.path
    try:
        import fixtures_broad
        _fixtures_module = fixtures_broad
        return _fixtures_module
    except ModuleNotFoundError:
        pass

    # 2. Dynamically search known candidate directories for pilot fixtures
    current_file = Path(__file__).resolve()
    candidate_dirs = [
        current_file.parents[3] / "tests" / "pilot",  # Repository root / tests / pilot
        current_file.parents[2] / "tests" / "pilot",  # Backend root / tests / pilot
        Path.cwd() / "tests" / "pilot",
        Path.cwd().parent / "tests" / "pilot",
        Path("/app/tests/pilot"),
    ]

    for candidate in candidate_dirs:
        if candidate.is_dir() and (candidate / "fixtures_broad.py").is_file():
            cand_str = str(candidate)
            if cand_str not in sys.path:
                sys.path.insert(0, cand_str)
            try:
                import fixtures_broad
                _fixtures_module = fixtures_broad
                return _fixtures_module
            except ModuleNotFoundError:
                continue

    logger.warning("Synthetic demo fixtures (fixtures_broad) could not be resolved.")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Synthetic demo fixtures are not available in this environment.",
    )


# ==============================================================================
# SCHEMAS
# ==============================================================================

class SyntheticPresetSummary(BaseModel):
    jd_id: str = Field(description="Unique synthetic JD identifier")
    title: str = Field(description="Human-readable technical job title")
    family: str = Field(description="Technical job family / stratum")
    paradigm: str = Field(description="Gate 1 experience paradigm")
    target_years: float | None = Field(default=None, description="Experience saturation target in years")
    required_skills: list[str] = Field(default_factory=list, description="Core required technical skills")
    candidate_count: int = Field(default=20, description="Total synthetic candidates in cohort")
    is_synthetic_demo: bool = Field(default=True, description="Strict synthetic sandbox flag")


class SyntheticPresetListResponse(BaseModel):
    total_presets: int
    presets: list[SyntheticPresetSummary]
    is_synthetic_demo: bool = True
    disclaimer: str = (
        "All data is 100% synthetic. Zero real candidate resumes, PII, or production database records are accessed."
    )


class DemoRankRequest(BaseModel):
    scoring_mode: str = Field(
        default="legacy",
        description="Scoring engine to evaluate: 'legacy' (categorical) or 'evidence' (Phase 5 evidence-based)",
    )


# ==============================================================================
# HELPER: IN-MEMORY SCORING & DUAL EVALUATION
# ==============================================================================

def _evaluate_synthetic_cohort(
    jd_id: str,
    active_mode: str = "legacy",
) -> dict[str, Any]:
    """
    Score all 20 synthetic candidates for a given synthetic JD under both
    Legacy and Evidence engines in memory, attaching score deltas and breakdowns.
    """
    fixtures = _get_fixtures()

    if jd_id not in fixtures.BROAD_JOB_DESCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synthetic preset '{jd_id}' not found.",
        )

    jd_obj: JobDescriptionObject = fixtures.BROAD_JOB_DESCRIPTIONS[jd_id]
    candidate_ids = fixtures.get_broad_jd_cohort_candidate_ids(jd_id)
    strata_meta = fixtures.JD_STRATA_METADATA.get(jd_id, {})
    preset_title = PRESET_TITLES.get(jd_id, jd_id)

    # Initialize independent in-memory engines
    engine_legacy = RankingEngine(use_evidence_based_experience=False)
    engine_evidence = RankingEngine(use_evidence_based_experience=True)

    scored_under_active: list[Any] = []
    candidates_data: dict[str, dict[str, Any]] = {}

    for cid in candidate_ids:
        match_result = fixtures.get_broad_candidate_match_result(cid)
        meta = fixtures.get_broad_candidate_meta(cid)

        # Compute dual scores
        res_leg = engine_legacy.score_candidate(
            match_result=match_result,
            job_description=jd_obj,
            use_evidence_based_experience=False,
        )
        res_evi = engine_evidence.score_candidate(
            match_result=match_result,
            job_description=jd_obj,
            use_evidence_based_experience=True,
        )

        leg_score = round(res_leg.final_score, 2) if res_leg.final_score is not None else None
        evi_score = round(res_evi.final_score, 2) if res_evi.final_score is not None else None
        score_delta = round(evi_score - leg_score, 2) if (evi_score is not None and leg_score is not None) else 0.0

        # Choose the active result object for ranking
        chosen_res = res_evi if active_mode == "evidence" else res_leg

        # Store rich metadata keyed by upload_id for deterministic lookup
        upload_id = match_result["upload_id"]
        candidates_data[upload_id] = {
            "candidate_id": cid,
            "name": meta["name"],
            "archetype": meta["archetype"],
            "edge_markers": meta["edge_markers"],
            "legacy_score": leg_score,
            "evidence_score": evi_score,
            "score_delta": score_delta,
            "legacy_breakdown": {k: v.model_dump() for k, v in res_leg.breakdown.items()},
            "evidence_breakdown": {k: v.model_dump() for k, v in res_evi.breakdown.items()},
            "legacy_experience_score": res_leg.breakdown["experience_relevance"].score if "experience_relevance" in res_leg.breakdown else None,
            "evidence_experience_score": res_evi.breakdown["experience_relevance"].score if "experience_relevance" in res_evi.breakdown else None,
            "active_mode_result": chosen_res,
        }
        scored_under_active.append(chosen_res)

    # Rank candidates based on active mode score
    active_engine = engine_evidence if active_mode == "evidence" else engine_legacy
    ranked_objs, unranked_objs = active_engine.rank_candidates(scored_under_active)

    def _build_candidate_card(cand_res, assigned_rank: int | None) -> dict[str, Any]:
        info = candidates_data.get(cand_res.upload_id, {})
        cid = info.get("candidate_id")

        res_dict = cand_res.model_dump()
        res_dict["rank"] = assigned_rank
        res_dict["candidate_id"] = cid
        res_dict["name"] = info.get("name", "Synthetic Candidate")
        res_dict["archetype"] = info.get("archetype", "")
        res_dict["edge_markers"] = info.get("edge_markers", [])
        res_dict["legacy_score"] = info.get("legacy_score")
        res_dict["evidence_score"] = info.get("evidence_score")
        res_dict["score_delta"] = info.get("score_delta", 0.0)
        res_dict["legacy_breakdown"] = info.get("legacy_breakdown", {})
        res_dict["evidence_breakdown"] = info.get("evidence_breakdown", {})
        res_dict["legacy_experience_score"] = info.get("legacy_experience_score")
        res_dict["evidence_experience_score"] = info.get("evidence_experience_score")
        res_dict["is_synthetic_demo"] = True
        return res_dict

    ranked_cards = [_build_candidate_card(c, idx) for idx, c in enumerate(ranked_objs, start=1)]
    unranked_cards = [_build_candidate_card(c, None) for c in unranked_objs]

    # Build structured JD object for frontend
    exp_req = jd_obj.experience_requirements[0] if jd_obj.experience_requirements else None
    structured_jd = {
        "jd_id": jd_id,
        "title": preset_title,
        "required_skills": jd_obj.required_skills,
        "responsibilities": jd_obj.responsibilities,
        "tools_and_technologies": jd_obj.tools_and_technologies,
        "experience_requirements": [
            {
                "minimum_years": exp_req.minimum_years if exp_req else None,
                "maximum_years": exp_req.maximum_years if exp_req else None,
                "preferred_domains": exp_req.preferred_domains if exp_req else [],
            }
        ] if exp_req else [],
    }

    return {
        "jd_id": jd_id,
        "preset_title": preset_title,
        "family": strata_meta.get("family", "Engineering"),
        "paradigm": strata_meta.get("paradigm", "Bounded"),
        "target_years": strata_meta.get("target_years"),
        "scoring_mode": active_mode,
        "is_synthetic_demo": True,
        "total_eligible": len(candidate_ids),
        "ranked_count": len(ranked_cards),
        "unranked_count": len(unranked_cards),
        "structured_jd": structured_jd,
        "ranked_candidates": ranked_cards,
        "unranked_candidates": unranked_cards,
        "disclaimer": "100% In-Memory Synthetic Data. Zero production database or real resume access.",
    }


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get(
    "/presets",
    response_model=SyntheticPresetListResponse,
    summary="List all 12 broad synthetic Job Description presets",
)
async def list_synthetic_presets() -> SyntheticPresetListResponse:
    """
    Returns available synthetic presets across all 6 technical strata.
    Purely in-memory; zero database access.
    """
    fixtures = _get_fixtures()
    presets = []
    for jd_id, jd_obj in fixtures.BROAD_JOB_DESCRIPTIONS.items():
        meta = fixtures.JD_STRATA_METADATA.get(jd_id, {})
        title = PRESET_TITLES.get(jd_id, jd_id)
        presets.append(
            SyntheticPresetSummary(
                jd_id=jd_id,
                title=title,
                family=meta.get("family", "Engineering"),
                paradigm=meta.get("paradigm", "Bounded"),
                target_years=meta.get("target_years"),
                required_skills=jd_obj.required_skills,
                candidate_count=20,
                is_synthetic_demo=True,
            )
        )

    return SyntheticPresetListResponse(
        total_presets=len(presets),
        presets=presets,
    )


@router.get(
    "/presets/{jd_id}",
    summary="Get details for a specific synthetic Job Description preset",
)
async def get_synthetic_preset(jd_id: str) -> dict[str, Any]:
    """
    Returns structured data for a single synthetic preset.
    Purely in-memory; zero database access.
    """
    fixtures = _get_fixtures()
    if jd_id not in fixtures.BROAD_JOB_DESCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Synthetic preset '{jd_id}' not found.",
        )

    jd_obj = fixtures.BROAD_JOB_DESCRIPTIONS[jd_id]
    meta = fixtures.JD_STRATA_METADATA.get(jd_id, {})
    title = PRESET_TITLES.get(jd_id, jd_id)
    exp_req = jd_obj.experience_requirements[0] if jd_obj.experience_requirements else None

    return {
        "jd_id": jd_id,
        "title": title,
        "family": meta.get("family", "Engineering"),
        "paradigm": meta.get("paradigm", "Bounded"),
        "target_years": meta.get("target_years"),
        "is_synthetic_demo": True,
        "structured_data": {
            "required_skills": jd_obj.required_skills,
            "responsibilities": jd_obj.responsibilities,
            "tools_and_technologies": jd_obj.tools_and_technologies,
            "experience_requirements": [
                {
                    "minimum_years": exp_req.minimum_years if exp_req else None,
                    "maximum_years": exp_req.maximum_years if exp_req else None,
                    "preferred_domains": exp_req.preferred_domains if exp_req else [],
                }
            ] if exp_req else [],
        },
    }


@router.get(
    "/cohort/{jd_id}",
    summary="Evaluate and retrieve ranked synthetic cohort for a preset",
)
async def get_synthetic_cohort_ranking(
    jd_id: str,
    scoring_mode: str = Query(
        default="legacy",
        pattern="^(legacy|evidence)$",
        description="Scoring engine to evaluate: 'legacy' or 'evidence'",
    ),
) -> dict[str, Any]:
    """
    Score and rank the 20 synthetic candidates for the specified preset.
    Computes both Legacy and Evidence scores in memory and returns full
    explainability breakdowns with zero database or network calls.
    """
    return _evaluate_synthetic_cohort(jd_id=jd_id, active_mode=scoring_mode)


@router.post(
    "/cohort/{jd_id}/rank",
    summary="Evaluate and retrieve ranked synthetic cohort with explicit options",
)
async def rank_synthetic_cohort(
    jd_id: str,
    request: DemoRankRequest = DemoRankRequest(),
) -> dict[str, Any]:
    """
    POST variant allowing flexible request bodies for synthetic ranking.
    """
    active_mode = "evidence" if request.scoring_mode.lower() == "evidence" else "legacy"
    return _evaluate_synthetic_cohort(jd_id=jd_id, active_mode=active_mode)
