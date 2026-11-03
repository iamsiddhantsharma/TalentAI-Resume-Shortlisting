"""
TalentAI — Phase 6: Ranking Engine Configuration Constants

Defines original base weights, thresholds, and categorical mappings
in a single centralized location to prevent hardcoding across modules.
Includes environment-driven feature flags for safe, phased scoring upgrades.
"""

import os
from typing import Final


def parse_bool_env(env_var_name: str, default: bool = False) -> bool:
    """
    Parse an environment-driven Boolean setting safely.

    Rules:
    - If absent or empty: return default (False).
    - Case-insensitive true values: 'true', '1', 'yes'.
    - Case-insensitive false values: 'false', '0', 'no'.
    - Any other value raises ValueError with a clear configuration message.
    """
    raw_val = os.getenv(env_var_name)
    if raw_val is None:
        return default

    cleaned = raw_val.strip()
    if not cleaned:
        return default

    lower_val = cleaned.lower()
    if lower_val in ("true", "1", "yes"):
        return True
    if lower_val in ("false", "0", "no"):
        return False

    raise ValueError(
        f"Invalid boolean configuration for '{env_var_name}': '{raw_val}'. "
        f"Expected one of: 'true', 'false', '1', '0', 'yes', 'no' (case-insensitive)."
    )


# ==============================================================================
# BASE WEIGHT CONFIGURATION (EXACT VALUES AS SPECIFIED IN PHASE 6)
# ==============================================================================

BASE_WEIGHTS: Final[dict[str, float]] = {
    "required_skills": 0.25,
    "responsibilities": 0.30,
    "tools_and_technologies": 0.10,
    "experience_relevance": 0.35,
}

# Verification assertion to ensure weights sum exactly to 1.0
assert abs(sum(BASE_WEIGHTS.values()) - 1.0) < 1e-6, "Base weights must sum to 1.0"

# ==============================================================================
# SEMANTIC RETRIEVAL THRESHOLDS
# ==============================================================================

# Retrieval threshold for responsibilities and tools semantic retrieval
SEMANTIC_RETRIEVAL_THRESHOLD: Final[float] = 0.65

# ==============================================================================
# CATEGORICAL EXPERIENCE RELEVANCE MAPPING
# ==============================================================================

# Deterministic mapping from Qwen categorical decisions to normalized values [0.0, 1.0]
CATEGORICAL_EXPERIENCE_SCORES: Final[dict[str, float]] = {
    "RELEVANT": 1.0,
    "AMBIGUOUS": 0.5,
    "INSUFFICIENT_INFORMATION": 0.0,
    "IRRELEVANT": 0.0,
}

# ==============================================================================
# FEATURE FLAGS (PHASE 5: EVIDENCE-BASED EXPERIENCE SCORING)
# ==============================================================================

# Feature flag toggling Phase 5 evidence-based experience scoring (E = 100 * S * D)
# When True (production default), the ranking engine uses continuous evidence-based experience.
# When False (rollback option), the ranking engine preserves legacy Phase 6 categorical scoring.
USE_EVIDENCE_BASED_EXPERIENCE: Final[bool] = parse_bool_env(
    "USE_EVIDENCE_BASED_EXPERIENCE",
    default=True,
)
