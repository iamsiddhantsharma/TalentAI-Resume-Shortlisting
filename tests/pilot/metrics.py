"""
TalentAI — Stage 5E.2: Pilot Evaluation Metrics Utilities

Pure, standalone implementation of all information retrieval, rank correlation,
tie measurement, and inter-rater reliability metrics specified in Stage 5E.2.1:
- Precision@K
- Recall@K (with exhaustive cohort denominator)
- NDCG@K (exponential gain 2^g - 1 and logarithmic discounting)
- Spearman's Rank Correlation (rho)
- Cohort Tie Rate and Top-K Shortlist Tie Rate
- Cohen's Kappa & Quadratic Weighted Kappa

Safety Invariant:
Pure mathematical functions; zero external dependencies; zero side effects.
"""

import math
from typing import Sequence


def human_grade_to_binary(grade: int) -> int:
    """
    Maps 4-level human relevance grade (0-3) to binary relevance.
    - Grade 3 (Exceptional Fit): Relevant (1)
    - Grade 2 (Good / Partial Fit): Relevant (1)
    - Grade 1 (Marginal Fit): Non-relevant (0)
    - Grade 0 (Unqualified / Irrelevant): Non-relevant (0)
    """
    return 1 if grade >= 2 else 0


def calculate_precision_at_k(ranked_grades: Sequence[int], k: int) -> float:
    """
    Computes Precision@K: Fraction of top-K candidates that are relevant (grade >= 2).
    """
    if k <= 0:
        return 0.0
    top_k = ranked_grades[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(human_grade_to_binary(g) for g in top_k)
    return round(relevant_count / float(len(top_k)), 4)


def calculate_recall_at_k(
    ranked_grades: Sequence[int],
    k: int,
    total_relevant: int,
) -> float:
    """
    Computes Recall@K: Fraction of all relevant candidates captured in the top-K.

    Denominator Note:
    In this pilot, every candidate in the cohort is exhaustively labeled,
    so total_relevant is known with complete mathematical certainty.
    """
    if total_relevant <= 0:
        # Edge case: If no candidate in the cohort is relevant,
        # return 1.0 if top_k contains 0 relevant, else 0.0.
        top_k = ranked_grades[:k]
        return 1.0 if sum(human_grade_to_binary(g) for g in top_k) == 0 else 0.0

    if k <= 0:
        return 0.0

    top_k = ranked_grades[:k]
    relevant_in_top_k = sum(human_grade_to_binary(g) for g in top_k)
    return round(min(1.0, relevant_in_top_k / float(total_relevant)), 4)


def calculate_dcg_at_k(ranked_grades: Sequence[int], k: int) -> float:
    """
    Computes Discounted Cumulative Gain at K using standard exponential relevance gain:
    gain(g) = 2^g - 1
    discount(i) = log2(i + 1) for i = 1, 2, ...
    """
    if k <= 0:
        return 0.0
    dcg = 0.0
    for i, grade in enumerate(ranked_grades[:k], start=1):
        gain = (2.0 ** float(grade)) - 1.0
        discount = math.log2(i + 1.0)
        dcg += gain / discount
    return dcg


def calculate_idcg_at_k(grades: Sequence[int], k: int) -> float:
    """
    Computes Ideal DCG at K by sorting all available cohort grades descending.
    """
    ideal_grades = sorted(grades, reverse=True)
    return calculate_dcg_at_k(ideal_grades, k)


def calculate_ndcg_at_k(ranked_grades: Sequence[int], k: int) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at K (NDCG@K).
    Returns 1.0 if IDCG == 0.0.
    """
    idcg = calculate_idcg_at_k(ranked_grades, k)
    if idcg <= 0.0:
        return 1.0
    dcg = calculate_dcg_at_k(ranked_grades, k)
    return round(min(1.0, dcg / idcg), 4)


def calculate_spearman_rho(ranks_a: Sequence[float], ranks_b: Sequence[float]) -> float:
    """
    Computes Spearman's rank correlation coefficient (rho) between two sequences.
    Handles tied fractional ranks via Pearson correlation of ranks.
    """
    n = len(ranks_a)
    if n != len(ranks_b) or n < 2:
        return 0.0

    mean_a = sum(ranks_a) / float(n)
    mean_b = sum(ranks_b) / float(n)

    cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(ranks_a, ranks_b))
    var_a = sum((a - mean_a) ** 2 for a in ranks_a)
    var_b = sum((b - mean_b) ** 2 for b in ranks_b)

    denom = math.sqrt(var_a * var_b)
    if denom <= 0.0:
        return 0.0
    return round(cov / denom, 4)


def calculate_tie_counts_and_rates(
    scores: Sequence[float],
    k: int = 5,
    epsilon: float = 1e-4,
) -> dict[str, float]:
    """
    Calculates candidate score ties across the entire cohort and top-K shortlist.

    Definition:
    Two candidates are tied if |score_i - score_j| < epsilon.
    """
    n = len(scores)
    total_pairs = (n * (n - 1)) // 2 if n >= 2 else 0
    tied_pairs = 0

    for i in range(n):
        for j in range(i + 1, n):
            if abs(scores[i] - scores[j]) < epsilon:
                tied_pairs += 1

    cohort_tie_rate = (tied_pairs / float(total_pairs)) if total_pairs > 0 else 0.0

    # Top-K tie analysis
    sorted_scores = sorted(scores, reverse=True)
    top_k_scores = sorted_scores[:k]
    k_len = len(top_k_scores)
    top_k_pairs = (k_len * (k_len - 1)) // 2 if k_len >= 2 else 0
    top_k_tied_pairs = 0

    for i in range(k_len):
        for j in range(i + 1, k_len):
            if abs(top_k_scores[i] - top_k_scores[j]) < epsilon:
                top_k_tied_pairs += 1

    top_k_tie_rate = (top_k_tied_pairs / float(top_k_pairs)) if top_k_pairs > 0 else 0.0

    return {
        "cohort_size": float(n),
        "total_pairs": float(total_pairs),
        "tied_pairs": float(tied_pairs),
        "cohort_tie_rate": round(cohort_tie_rate, 4),
        "top_k_size": float(k_len),
        "top_k_pairs": float(top_k_pairs),
        "top_k_tied_pairs": float(top_k_tied_pairs),
        "top_k_tie_rate": round(top_k_tie_rate, 4),
    }


def calculate_cohen_kappa(
    ratings_1: Sequence[int],
    ratings_2: Sequence[int],
    categories: Sequence[int] = (0, 1, 2, 3),
    quadratic_weighted: bool = True,
) -> float:
    """
    Calculates Cohen's Kappa between two raters.
    Supports unweighted and quadratic weighted kappa for ordinal scales.
    """
    n = len(ratings_1)
    if n != len(ratings_2) or n == 0:
        return 0.0

    cat_to_idx = {cat: idx for idx, cat in enumerate(categories)}
    k = len(categories)

    # Build confusion matrix
    matrix = [[0 for _ in range(k)] for _ in range(k)]
    for r1, r2 in zip(ratings_1, ratings_2):
        if r1 in cat_to_idx and r2 in cat_to_idx:
            matrix[cat_to_idx[r1]][cat_to_idx[r2]] += 1

    total = float(n)

    # Observed agreement
    if not quadratic_weighted:
        po = sum(matrix[i][i] for i in range(k)) / total
        pe = sum(
            (sum(matrix[i][j] for j in range(k)) * sum(matrix[j][i] for j in range(k)))
            for i in range(k)
        ) / (total * total)
        if pe >= 1.0:
            return 1.0
        return round((po - pe) / (1.0 - pe), 4)

    # Quadratic weighted kappa
    weights = [
        [1.0 - (((i - j) ** 2) / float((k - 1) ** 2)) for j in range(k)]
        for i in range(k)
    ]

    row_totals = [sum(matrix[i][j] for j in range(k)) for i in range(k)]
    col_totals = [sum(matrix[j][i] for j in range(k)) for i in range(k)]

    po = sum(weights[i][j] * (matrix[i][j] / total) for i in range(k) for j in range(k))
    pe = sum(
        weights[i][j] * (row_totals[i] * col_totals[j] / (total * total))
        for i in range(k)
        for j in range(k)
    )

    if pe >= 1.0:
        return 1.0
    return round((po - pe) / (1.0 - pe), 4)
