"""
TalentAI — Phase 4: Semantic Similarity Benchmark & Calibration Evaluator

Evaluates semantic similarity between candidate work summaries and JD experience
requirements across 50 benchmark pairs using BAAI/bge-large-en-v1.5 embeddings.

Generates raw similarity distributions, confusion matrices across candidate
thresholds (0.55 to 0.85), subcategory breakdowns, and calibrated similarity distributions.
"""

import json
import math
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.embedding_service import embedding_service


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two unit vectors (dot product)."""
    return float(sum(a * b for a, b in zip(vec_a, vec_b)))


def compute_stats(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "std": 0.0}
    sorted_v = sorted(values)
    n = len(values)
    mean_val = sum(values) / n
    median_val = sorted_v[n // 2] if n % 2 != 0 else (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0
    var = sum((x - mean_val) ** 2 for x in values) / n
    std_val = math.sqrt(var)
    return {
        "count": n,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(mean_val, 4),
        "median": round(median_val, 4),
        "std": round(std_val, 4),
    }


def calibrate_similarity(raw_sim: float, tau: float) -> float:
    """Calibrate similarity using formula: clamp((raw_sim - tau) / (1 - tau), 0, 1)."""
    if raw_sim < tau:
        return 0.0
    if tau >= 1.0:
        return 1.0 if raw_sim >= 1.0 else 0.0
    val = (raw_sim - tau) / (1.0 - tau)
    return max(0.0, min(1.0, val))


def run_benchmark():
    benchmark_path = backend_dir / "test_data" / "evaluation" / "experience_similarity_benchmark.json"
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark file not found at {benchmark_path}")

    with open(benchmark_path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    print(f"Loaded {len(pairs)} benchmark pairs from {benchmark_path}")
    print("Generating embeddings using BAAI/bge-large-en-v1.5 ...")

    # Evaluate each pair
    evaluated_pairs = []
    for item in pairs:
        pair_id = item["id"]
        category = item["category"]
        cand_text = item["candidate_work_summary"]
        jd_text = item["jd_requirement"]
        expected = item["expected_relevance"]
        rationale = item["rationale"]

        # Generate embeddings
        cand_emb = embedding_service.generate_embedding(cand_text)
        jd_emb = embedding_service.generate_embedding(jd_text)

        raw_sim = cosine_similarity(cand_emb, jd_emb)

        evaluated_pairs.append({
            "id": pair_id,
            "category": category,
            "expected_relevance": expected,
            "candidate_work_summary": cand_text,
            "jd_requirement": jd_text,
            "rationale": rationale,
            "raw_similarity": round(raw_sim, 4),
        })

    # Group raw similarities by class/category
    categories = ["genuine_ml", "transferable_backend", "unrelated", "edge_case"]
    cat_sims = {c: [p["raw_similarity"] for p in evaluated_pairs if p["category"] == c] for c in categories}
    
    # Also separate edge cases into expected True vs False
    edge_cases_pos = [p["raw_similarity"] for p in evaluated_pairs if p["category"] == "edge_case" and p["expected_relevance"]]
    edge_cases_neg = [p["raw_similarity"] for p in evaluated_pairs if p["category"] == "edge_case" and not p["expected_relevance"]]

    all_pos = [p["raw_similarity"] for p in evaluated_pairs if p["expected_relevance"]]
    all_neg = [p["raw_similarity"] for p in evaluated_pairs if not p["expected_relevance"]]

    print("\n" + "=" * 80)
    print("RAW SIMILARITY DISTRIBUTIONS BY BENCHMARK CATEGORY")
    print("=" * 80)
    print(f"{'Category':<25} | {'Count':<5} | {'Min':<7} | {'Max':<7} | {'Mean':<7} | {'Median':<7} | {'Std':<7}")
    print("-" * 80)
    for c in categories:
        st = compute_stats(cat_sims[c])
        print(f"{c:<25} | {st['count']:<5} | {st['min']:<7} | {st['max']:<7} | {st['mean']:<7} | {st['median']:<7} | {st['std']:<7}")
    
    st_edge_pos = compute_stats(edge_cases_pos)
    st_edge_neg = compute_stats(edge_cases_neg)
    print(f"{'  - edge_case (expected=True)':<25} | {st_edge_pos['count']:<5} | {st_edge_pos['min']:<7} | {st_edge_pos['max']:<7} | {st_edge_pos['mean']:<7} | {st_edge_pos['median']:<7} | {st_edge_pos['std']:<7}")
    print(f"{'  - edge_case (expected=False)':<25} | {st_edge_neg['count']:<5} | {st_edge_neg['min']:<7} | {st_edge_neg['max']:<7} | {st_edge_neg['mean']:<7} | {st_edge_neg['median']:<7} | {st_edge_neg['std']:<7}")

    st_pos = compute_stats(all_pos)
    st_neg = compute_stats(all_neg)
    print("-" * 80)
    print(f"{'ALL RELEVANT (Ground Truth)':<25} | {st_pos['count']:<5} | {st_pos['min']:<7} | {st_pos['max']:<7} | {st_pos['mean']:<7} | {st_pos['median']:<7} | {st_pos['std']:<7}")
    print(f"{'ALL IRRELEVANT (Ground Truth)':<25} | {st_neg['count']:<5} | {st_neg['min']:<7} | {st_neg['max']:<7} | {st_neg['mean']:<7} | {st_neg['median']:<7} | {st_neg['std']:<7}")
    print("=" * 80)

    # Threshold evaluation sweep
    thresholds = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    total_pos = len(all_pos)
    total_neg = len(all_neg)

    threshold_results = []

    print("\n" + "=" * 90)
    print("METRICS ACROSS CANDIDATE THRESHOLDS (tau from 0.55 to 0.85)")
    print("=" * 90)
    print(f"{'Tau':<6} | {'TP':<4} | {'FP':<4} | {'TN':<4} | {'FN':<4} | {'FPR':<7} | {'FNR':<7} | {'Precision':<9} | {'Recall':<7} | {'F1':<7}")
    print("-" * 90)

    for tau in thresholds:
        tp = sum(1 for p in evaluated_pairs if p["expected_relevance"] and p["raw_similarity"] >= tau)
        fp = sum(1 for p in evaluated_pairs if not p["expected_relevance"] and p["raw_similarity"] >= tau)
        tn = sum(1 for p in evaluated_pairs if not p["expected_relevance"] and p["raw_similarity"] < tau)
        fn = sum(1 for p in evaluated_pairs if p["expected_relevance"] and p["raw_similarity"] < tau)

        fpr = fp / total_neg if total_neg > 0 else 0.0
        fnr = fn / total_pos if total_pos > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Subcategory breakdown of false positives and false negatives
        fp_backend = sum(1 for p in evaluated_pairs if p["category"] == "transferable_backend" and p["raw_similarity"] >= tau)
        fp_unrelated = sum(1 for p in evaluated_pairs if p["category"] == "unrelated" and p["raw_similarity"] >= tau)
        fp_edge = sum(1 for p in evaluated_pairs if p["category"] == "edge_case" and not p["expected_relevance"] and p["raw_similarity"] >= tau)

        fn_genuine_ml = sum(1 for p in evaluated_pairs if p["category"] == "genuine_ml" and p["raw_similarity"] < tau)
        fn_edge = sum(1 for p in evaluated_pairs if p["category"] == "edge_case" and p["expected_relevance"] and p["raw_similarity"] < tau)

        threshold_results.append({
            "tau": tau,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "fpr": round(fpr, 4),
            "fnr": round(fnr, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "breakdown": {
                "fp_transferable_backend": fp_backend,
                "fp_unrelated": fp_unrelated,
                "fp_edge_case": fp_edge,
                "fn_genuine_ml": fn_genuine_ml,
                "fn_edge_case": fn_edge,
            }
        })

        print(f"{tau:<6.2f} | {tp:<4} | {fp:<4} | {tn:<4} | {fn:<4} | {fpr:<7.4f} | {fnr:<7.4f} | {precision:<9.4f} | {recall:<7.4f} | {f1:<7.4f}")

    print("=" * 90)

    # Detailed breakdown per threshold
    print("\n" + "=" * 90)
    print("FALSE POSITIVE & FALSE NEGATIVE ERROR BREAKDOWN BY SUBCATEGORY")
    print("=" * 90)
    print(f"{'Tau':<6} | {'FP Backend (/15)':<17} | {'FP Unrelated (/10)':<19} | {'FP Edge (/5)':<14} | {'FN ML (/15)':<12} | {'FN Edge (/5)':<12}")
    print("-" * 90)
    for r in threshold_results:
        b = r["breakdown"]
        print(f"{r['tau']:<6.2f} | {b['fp_transferable_backend']:<17} | {b['fp_unrelated']:<19} | {b['fp_edge_case']:<14} | {b['fn_genuine_ml']:<12} | {b['fn_edge_case']:<12}")
    print("=" * 90)

    # Save detailed evaluation artifact
    output_path = backend_dir / "test_data" / "evaluation" / "similarity_calibration_results.json"
    evaluation_payload = {
        "model": embedding_service.MODEL_NAME,
        "embedding_dimension": 1024,
        "total_pairs": len(evaluated_pairs),
        "category_statistics": {c: compute_stats(cat_sims[c]) for c in categories},
        "ground_truth_statistics": {
            "relevant": st_pos,
            "irrelevant": st_neg,
        },
        "threshold_metrics": threshold_results,
        "evaluated_pairs": evaluated_pairs,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_payload, f, indent=2)

    print(f"\nSaved complete calibration results to {output_path}")


if __name__ == "__main__":
    run_benchmark()
