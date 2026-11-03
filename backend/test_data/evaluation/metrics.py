"""
TalentAI — Phase 9.2: Ranking Quality Evaluation Metrics

Pure, deterministic implementations of information retrieval and ranking metrics:
1. Precision@K
2. Discounted Cumulative Gain (DCG@K) & Normalized DCG (NDCG@K)
3. Spearman's Rank Correlation (rho)
4. Incomplete Candidate Separation Rate (ICSR)

All metrics include safe boundary handling for:
- K exceeding cohort size (clamped to cohort size)
- Zero IDCG (all candidates having 0 relevance)
- Missing ground-truth annotations
- Tied candidates (deterministic presentation tie-breaker applied)
- Exclusion of incomplete candidates from numeric score ranking
"""

import math
from typing import Any, Sequence
from app.ranking.ranking_schemas import CandidateRankingResult


def calculate_precision_at_k(
    ranked_candidates: Sequence[CandidateRankingResult],
    ground_truth: dict[str, int],
    k: int,
    relevance_threshold: int = 2,
) -> float:
    """
    Calculate Precision@K: Fraction of top-K candidates that meet or exceed
    the relevance threshold (default: >= 2 for good/exceptional fit).

    Safe Boundary Behavior:
    - If cohort is empty: returns 0.0.
    - If K > len(ranked_candidates): clamps K to len(ranked_candidates).
    - Unannotated candidates are treated as non-relevant (0).
    """
    if not ranked_candidates or k <= 0:
        return 0.0

    eval_k = min(k, len(ranked_candidates))
    top_k = ranked_candidates[:eval_k]

    relevant_count = 0
    for cand in top_k:
        grade = ground_truth.get(cand.filename, 0)
        if grade >= relevance_threshold:
            relevant_count += 1

    return round(float(relevant_count) / float(eval_k), 4)


def calculate_dcg_at_k(
    relevance_scores: Sequence[int],
    k: int,
) -> float:
    """
    Calculate Discounted Cumulative Gain at K using standard logarithmic discounting:
        DCG@K = sum_{i=1}^K (2^{r_i} - 1) / log_2(i + 1)
    """
    if not relevance_scores or k <= 0:
        return 0.0

    eval_k = min(k, len(relevance_scores))
    dcg = 0.0
    for i in range(eval_k):
        rel = relevance_scores[i]
        # 1-indexed position: i + 1. log2(i + 2) is log2(rank + 1)
        discount = math.log2(i + 2)
        gain = (2.0 ** rel) - 1.0
        dcg += gain / discount

    return dcg


def calculate_ndcg_at_k(
    ranked_candidates: Sequence[CandidateRankingResult],
    ground_truth: dict[str, int],
    k: int,
    handle_ties: bool = False,
) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain at K:
        NDCG@K = DCG@K / IDCG@K

    Safe Boundary Behavior:
    - If cohort is empty: returns 0.0.
    - If K > len(ranked_candidates): clamps K to len(ranked_candidates).
    - If IDCG@K == 0.0 (all ground truth scores are 0): returns 1.0 if DCG@K == 0.0,
      since the ranking trivially satisfies the zero-relevance requirement.
    - If handle_ties=True: for candidates with identical scores spanning the cutoff K,
      computes the expected gain across permutations of the tied block.
    """
    if not ranked_candidates or k <= 0:
        return 0.0

    eval_k = min(k, len(ranked_candidates))

    if not handle_ties:
        actual_relevance = [
            ground_truth.get(c.filename, 0) for c in ranked_candidates[:eval_k]
        ]
        dcg = calculate_dcg_at_k(actual_relevance, eval_k)
    else:
        # Group candidates by identical final_score
        # Compute expected gain for each rank position
        dcg = 0.0
        n = len(ranked_candidates)
        i = 0
        while i < eval_k and i < n:
            score = ranked_candidates[i].final_score
            j = i
            while j + 1 < n and ranked_candidates[j + 1].final_score == score:
                j += 1
            # Candidates from i to j have the exact same score
            block_relevance = [ground_truth.get(ranked_candidates[idx].filename, 0) for idx in range(i, j + 1)]
            avg_gain = sum((2.0 ** r) - 1.0 for r in block_relevance) / len(block_relevance)
            # Add discount for each position within eval_k
            for pos in range(i, min(j + 1, eval_k)):
                dcg += avg_gain / math.log2(pos + 2)
            i = j + 1

    # Ideal ranking: sort all available ground truth annotations in descending order
    all_relevance_desc = sorted(
        [ground_truth.get(c.filename, 0) for c in ranked_candidates],
        reverse=True,
    )
    idcg = calculate_dcg_at_k(all_relevance_desc, eval_k)

    if idcg == 0.0:
        return 1.0 if dcg == 0.0 else 0.0

    return round(dcg / idcg, 4)


def calculate_spearman_correlation(
    ranked_candidates: Sequence[CandidateRankingResult],
    ground_truth: dict[str, int],
) -> float | None:
    """
    Calculate Spearman's rank correlation coefficient (rho) between candidate
    system ranking positions (1 to N) and human relevance grades.

    Safe Boundary Behavior:
    - Requires at least 2 candidates with known ground truth.
    - If all relevance grades are identical (zero variance), correlation
      is mathematically undefined; returns None.
    """
    pairs: list[tuple[float, float]] = []
    for i, cand in enumerate(ranked_candidates, start=1):
        if cand.filename in ground_truth:
            # Model rank is i (1 is best). For correlation with grade where higher is better,
            # we use candidate final_score or inverted rank.
            pairs.append((float(cand.final_score if cand.final_score is not None else 0.0), float(ground_truth[cand.filename])))

    n = len(pairs)
    if n < 2:
        return None

    scores = [p[0] for p in pairs]
    grades = [p[1] for p in pairs]

    # Check for zero variance
    mean_s = sum(scores) / n
    mean_g = sum(grades) / n

    var_s = sum((s - mean_s) ** 2 for s in scores)
    var_g = sum((g - mean_g) ** 2 for g in grades)

    if var_s == 0.0 or var_g == 0.0:
        return None

    # Compute rank-based Pearson correlation (Spearman rho)
    def to_ranks(vals: list[float], reverse: bool = False) -> list[float]:
        # Handle ties using fractional ranks
        sorted_indices = sorted(range(n), key=lambda idx: vals[idx], reverse=reverse)
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[sorted_indices[j + 1]] == vals[sorted_indices[i]]:
                j += 1
            # Average rank for ties (1-indexed)
            avg_rank = (i + 1 + j + 1) / 2.0
            for k_idx in range(i, j + 1):
                ranks[sorted_indices[k_idx]] = avg_rank
            i = j + 1
        return ranks

    r_s = to_ranks(scores, reverse=True)  # Higher score = lower rank number (1 is highest)
    r_g = to_ranks(grades, reverse=True)  # Higher grade = lower rank number (1 is highest)

    d_sq_sum = sum((r_s[k] - r_g[k]) ** 2 for k in range(n))
    rho = 1.0 - (6.0 * d_sq_sum) / (n * (n * n - 1.0))
    return round(rho, 4)


def calculate_incomplete_separation_rate(
    unranked_candidates: Sequence[CandidateRankingResult],
    expected_failed_filenames: Sequence[str],
) -> float:
    """
    Calculate Incomplete Candidate Separation Rate (ICSR):
        ICSR = (Number of technical failure candidates correctly placed in unranked)
               / (Total technical failure candidates)

    Target: 1.0 (100%).
    """
    if not expected_failed_filenames:
        return 1.0

    unranked_filenames = {
        c.filename for c in unranked_candidates
        if c.status == "incomplete" and c.final_score is None and c.rank is None
    }

    correctly_separated = sum(
        1 for f in expected_failed_filenames if f in unranked_filenames
    )

    return round(float(correctly_separated) / float(len(expected_failed_filenames)), 4)
