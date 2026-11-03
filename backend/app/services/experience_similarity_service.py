"""
TalentAI — Phase 4: Semantic Similarity Benchmark & Calibration Service

Calculates and calibrates semantic similarity between verified candidate
relevant work summaries and Job Description experience requirements.

Key Safeguards:
1. Zero-Credit Safeguard: Only roles verified as RELEVANT or PARTIALLY_RELEVANT
   with a non-empty, evidence-based relevant_work_summary receive similarity credit.
2. Unrelated / Ambiguous / Insufficient Information roles strictly return 0.0.
3. Missing or empty summaries return 0.0 with transparent diagnostics.
4. Preserves complete explainability: raw similarity, calibrated similarity,
   tau threshold, model identity, source summary, and matched JD requirement.
"""

import math
from typing import Any

from app.services.embedding_service import embedding_service


class ExperienceSimilarityService:
    """
    Evidence-based Experience Semantic Similarity Service.

    Implements cosine similarity and linear calibration:
        S = clamp((raw_similarity - tau) / (1.0 - tau), 0.0, 1.0)
    """

    MODEL_NAME = "BAAI/bge-large-en-v1.5"
    DEFAULT_TAU = 0.65

    # =========================================================================
    # 1. PURE MATHEMATICAL FUNCTIONS
    # =========================================================================

    @staticmethod
    def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Clamp float value into [min_val, max_val]."""
        return max(min_val, min(value, max_val))

    def cosine_similarity(
        self,
        vector_a: list[float],
        vector_b: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Because BGE embeddings are generated with normalize_embeddings=True,
        cosine similarity is mathematically equivalent to the dot product.
        Explicit magnitude division is provided for robustness against unnormalized vectors.
        """
        if not vector_a or not vector_b:
            raise ValueError("Vectors cannot be empty.")

        if len(vector_a) != len(vector_b):
            raise ValueError(
                f"Vector dimension mismatch: {len(vector_a)} vs {len(vector_b)}."
            )

        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        mag_a = math.sqrt(sum(a * a for a in vector_a))
        mag_b = math.sqrt(sum(b * b for b in vector_b))

        if mag_a == 0.0 or mag_b == 0.0:
            raise ValueError("Cannot calculate cosine similarity for a zero vector.")

        cos_sim = dot_product / (mag_a * mag_b)
        return float(self.clamp(cos_sim, -1.0, 1.0))

    def calibrate_similarity(
        self,
        raw_similarity: float,
        tau: float = DEFAULT_TAU,
    ) -> float:
        """
        Calibrate raw cosine similarity against provisional threshold tau:
            S = clamp((raw_similarity - tau) / (1.0 - tau), 0.0, 1.0)
            if raw_similarity < tau: S = 0.0
        """
        if raw_similarity < tau:
            return 0.0

        if tau >= 1.0:
            return 1.0 if raw_similarity >= 1.0 else 0.0

        normalized = (raw_similarity - tau) / (1.0 - tau)
        return float(self.clamp(normalized, 0.0, 1.0))

    # =========================================================================
    # 2. EVIDENCE & ZERO-CREDIT SAFEGUARDS
    # =========================================================================

    def evaluate_experience_similarity(
        self,
        decision: str | None,
        relevant_work_summary: str | None,
        jd_requirements: list[str] | str,
        tau: float = DEFAULT_TAU,
        candidate_embedding: list[float] | None = None,
        jd_embeddings: list[list[float]] | dict[str, list[float]] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate semantic similarity for a candidate experience entry.

        Enforces all zero-credit safeguards:
        - If decision is not RELEVANT or PARTIALLY_RELEVANT: zero credit.
        - If relevant_work_summary is None or empty: zero credit.
        - If jd_requirements is empty: zero credit.

        Returns explainable dictionary containing raw and calibrated scores.
        """
        # Normalize decision string
        norm_decision = decision.strip().upper() if decision and isinstance(decision, str) else None

        # Base response structure
        base_result = {
            "eligible": False,
            "decision": norm_decision,
            "raw_similarity": 0.0,
            "calibrated_similarity": 0.0,
            "tau": tau,
            "model_name": self.MODEL_NAME,
            "relevant_work_summary": relevant_work_summary,
            "best_matching_requirement": None,
            "all_domain_similarities": [],
            "diagnostic_status": "unspecified",
            "diagnostic_message": "",
        }

        # Safeguard 1: Relevance decision check
        if norm_decision not in ("RELEVANT", "PARTIALLY_RELEVANT"):
            base_result["diagnostic_status"] = "zero_credit_non_relevant"
            base_result["diagnostic_message"] = (
                f"Zero similarity credit: role classified as {norm_decision or 'UNSPECIFIED'}."
            )
            return base_result

        # Safeguard 2: Verified relevant work summary check
        if not relevant_work_summary or not relevant_work_summary.strip():
            base_result["diagnostic_status"] = "missing_work_summary"
            base_result["diagnostic_message"] = (
                "Zero similarity credit: verified relevant work summary is missing or empty."
            )
            return base_result

        clean_summary = relevant_work_summary.strip()

        # Safeguard 3: JD requirements check
        req_list: list[str] = []
        if isinstance(jd_requirements, str):
            if jd_requirements.strip():
                req_list = [jd_requirements.strip()]
        elif isinstance(jd_requirements, list):
            req_list = [r.strip() for r in jd_requirements if r and r.strip()]

        if not req_list:
            base_result["diagnostic_status"] = "missing_jd_requirements"
            base_result["diagnostic_message"] = (
                "Zero similarity credit: Job Description defines no experience requirements or domains."
            )
            return base_result

        # ---------------------------------------------------------------------
        # EMBEDDING GENERATION / RETRIEVAL
        # ---------------------------------------------------------------------
        if candidate_embedding is not None:
            cand_emb = candidate_embedding
        else:
            cand_emb = embedding_service.generate_embedding(clean_summary)

        # Compute similarities across all JD requirements/domains
        domain_sims: list[dict[str, Any]] = []
        best_sim = -1.0
        best_req: str | None = None

        for idx, req in enumerate(req_list):
            if isinstance(jd_embeddings, dict) and req in jd_embeddings:
                req_emb = jd_embeddings[req]
            elif isinstance(jd_embeddings, list) and idx < len(jd_embeddings):
                req_emb = jd_embeddings[idx]
            else:
                req_emb = embedding_service.generate_embedding(req)

            sim = self.cosine_similarity(cand_emb, req_emb)
            domain_sims.append({
                "requirement": req,
                "raw_similarity": round(sim, 4),
            })

            if sim > best_sim:
                best_sim = sim
                best_req = req

        raw_sim_clamped = self.clamp(best_sim, -1.0, 1.0)
        calibrated_sim = self.calibrate_similarity(raw_sim_clamped, tau=tau)

        return {
            "eligible": True,
            "decision": norm_decision,
            "raw_similarity": round(raw_sim_clamped, 4),
            "calibrated_similarity": round(calibrated_sim, 4),
            "tau": tau,
            "model_name": self.MODEL_NAME,
            "relevant_work_summary": clean_summary,
            "best_matching_requirement": best_req,
            "all_domain_similarities": domain_sims,
            "diagnostic_status": "similarity_calculated",
            "diagnostic_message": (
                f"Calibrated similarity {calibrated_sim:.4f} "
                f"(raw: {raw_sim_clamped:.4f}, tau: {tau}, matched: '{best_req}')."
            ),
        }


# Singleton instance
experience_similarity_service = ExperienceSimilarityService()
