"""
TalentAI — Phase 9.3: Metrics Calculator

Calculates inter-rater agreement (Weighted Cohen's Kappa), model-human rank
correlation (Kendall's Tau-b, Spearman's Rho), Information Retrieval metrics
(Precision@K, Tie-Aware NDCG@K), and Technical Separation Rates.
"""

import math
from typing import Sequence
from app.ranking.ranking_schemas import CandidateRankingResult
from test_data.evaluation.metrics import (
    calculate_dcg_at_k,
    calculate_incomplete_separation_rate,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_spearman_correlation,
)


def calculate_weighted_cohen_kappa(
    rater1_grades: Sequence[int],
    rater2_grades: Sequence[int],
    weights: str = "quadratic",
) -> float:
    """
    Calculate Weighted Cohen's Kappa for ordinal agreement between two raters.
    weights: 'linear' or 'quadratic'.

    Formula:
        w_ij = 1 - |i - j| / (k - 1)  (linear)
        w_ij = 1 - (i - j)^2 / (k - 1)^2  (quadratic)
        kappa_w = (Observed_w - Expected_w) / (1 - Expected_w)
    """
    if len(rater1_grades) != len(rater2_grades):
        raise ValueError("Raters must have evaluated the same number of candidates.")

    n = len(rater1_grades)
    if n == 0:
        return 1.0

    min_c = min(min(rater1_grades), min(rater2_grades))
    max_c = max(max(rater1_grades), max(rater2_grades))
    k = max_c - min_c
    if k == 0:
        return 1.0

    # Build weight matrix
    w: dict[tuple[int, int], float] = {}
    for i in range(min_c, max_c + 1):
        for j in range(min_c, max_c + 1):
            if weights == "linear":
                w[(i, j)] = 1.0 - (abs(i - j) / float(k))
            else:  # quadratic
                w[(i, j)] = 1.0 - (((i - j) ** 2) / float(k ** 2))

    # Observed agreement
    obs = sum(w[(rater1_grades[idx], rater2_grades[idx])] for idx in range(n))

    # Expected agreement
    hist1 = {c: sum(1 for g in rater1_grades if g == c) for c in range(min_c, max_c + 1)}
    hist2 = {c: sum(1 for g in rater2_grades if g == c) for c in range(min_c, max_c + 1)}
    exp = sum(
        w[(i, j)] * (hist1[i] * hist2[j])
        for i in range(min_c, max_c + 1)
        for j in range(min_c, max_c + 1)
    ) / float(n)

    if (n - exp) == 0.0:
        return 1.0

    kappa = (obs - exp) / (n - exp)
    return round(kappa, 4)


def calculate_kendall_tau_b(
    scores: Sequence[float],
    grades: Sequence[float],
) -> float | None:
    """
    Calculate Kendall's Tau-b rank correlation coefficient between model scores
    and human consensus grades, accounting for ties in both variables.

        tau_b = (C - D) / sqrt((C + D + Tx) * (C + D + Ty))
    """
    if len(scores) != len(grades):
        raise ValueError("Scores and grades must have equal length.")

    n = len(scores)
    if n < 2:
        return None

    c = 0
    d = 0
    tx = 0
    ty = 0

    for i in range(n):
        for j in range(i + 1, n):
            dx = scores[i] - scores[j]
            dy = grades[i] - grades[j]

            if dx == 0 and dy == 0:
                tx += 1
                ty += 1
            elif dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                c += 1
            else:
                d += 1

    denom = math.sqrt((c + d + tx) * (c + d + ty))
    if denom == 0.0:
        return 0.0

    return round((c - d) / denom, 4)
