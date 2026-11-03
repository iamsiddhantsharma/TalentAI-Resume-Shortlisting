# TalentAI — Stage 5E.2: Isolated Synthetic Pilot Runner

## Overview

This directory contains the standalone, isolated, offline evaluation runner and synthetic fixtures designed in **Stage 5E.2.1** for evaluating evidence-based experience ranking ($E = 100 \cdot S_{\text{agg}} \cdot D_{\text{global}}$) against legacy categorical ranking.

**Current Stage Status:** Stage 5E.2.2 Construction Complete.  
**Execution Status:** NOT EXECUTED. Awaiting explicit user authorization.

---

## Architecture & Safety Isolation

The runner operates under complete physical, database, and process isolation:
1. **Zero Database Dependencies:** No connections to MongoDB `talent_ai`. No documents read, written, or modified.
2. **Zero PII & 100% Synthetic:** All 3 Job Descriptions, 24 candidate profiles, and work histories are entirely fictional and generated in-memory in `fixtures.py`. No real resumes or candidate identities are referenced.
3. **Constructor-Level Engine Mode Selection:** Uses independent instances of `RankingEngine(use_evidence_based_experience=False)` and `RankingEngine(use_evidence_based_experience=True)`. The global feature flag `USE_EVIDENCE_BASED_EXPERIENCE` remains strictly `False`.
4. **Zero Mutation Guarantee:** Candidate match results are supplied via deep-copied fixtures, preventing state leakage or mutation across engine calls.
5. **Zero Live API Interaction:** No HTTP requests are issued; no batches are created, superseded, or activated.

---

## File Structure

```
tests/pilot/
├── README.md                  # This specification and execution guide
├── fixtures.py                # 3 synthetic JDs, 24 synthetic candidate match results, and human annotations
├── metrics.py                 # Pure mathematical implementations of P@K, Recall@K, NDCG@K, Spearman rho, Tie rates
└── test_stage_5e2_pilot.py    # Standalone test runner implementing Groups A, B, C, D, and E
```

---

## Implemented Test Groups

- **Group A: Legacy and Evidence Engine Comparison**
  - Identical candidate input verification
  - Invariance of Components A (Skills), B (Responsibilities), and C (Tools)
  - Final score delta strictly attributable to Component D: $\Delta_{\text{final}} = 0.35 \times (E_{\text{evidence}} - E_{\text{legacy}})$
  - Preservation of global feature flag `USE_EVIDENCE_BASED_EXPERIENCE = False`
- **Group B: Experience Scoring Behavior & Edge Cases**
  - Bounded range duration saturation ($D=1.000$)
  - Proportional duration damping ($D \in (0, 1)$)
  - Irrelevant career backgrounds (Rule 10 zeroing)
  - Missing employment dates safeguard ($D=0.000, E=0.00$)
  - Gate 1 Rule C (G1-C) unbounded requirements safeguard
  - Multiple roles within the same domain using per-domain maximum similarity
  - Unsupported preferred domain zero-filling
  - Case-insensitive preferred domain deduplication
- **Group C: Duration Pooling (Approved Time-Sliced Weighted Algorithm)**
  - Verification of `experience_matching_service.calculate_weighted_non_overlapping_duration`
  - Preservation of full credit for fully relevant roles during overlaps with partially relevant roles
  - Verification that concurrent intervals are not double-counted
  - Rejection of unweighted interval union in favor of the approved time-sliced rule
- **Group D: Pilot Metric Preparation Utilities**
  - Precision@K with binary relevance cutoff ($\text{grade} \ge 2$)
  - Recall@K with exact, exhaustive cohort denominator ($R_{\text{total}}$)
  - NDCG@K using exponential gains ($2^g - 1$) and ideal sorting
  - Spearman rank correlation ($\rho$)
  - Cohort-wide and Top-5 shortlist tie rates
  - Advisory threshold verification (non-blocking for production release)
- **Group E: Explanation, Traceability, and Provenance**
  - Full provenance fields (`supporting_role`, `supporting_company`, `calibrated_similarity`, `relevant_work_summary`)
  - Missing-date diagnostic banners
  - G1-C diagnostic notes and alerts
  - Distinction between zero score and missing information
  - Domain evidence preservation even when G1-C duration is zero

---

## Safe Future Execution Instructions

When explicitly authorized by the user for Stage 5E.2.3 execution:

```bash
# Run using Python's standard unittest runner from project root
python -m unittest tests/pilot/test_stage_5e2_pilot.py

# Or run using pytest
pytest tests/pilot/test_stage_5e2_pilot.py -v
```

> [!CAUTION]
> **Do not execute without explicit user authorization.**  
> Keep `USE_EVIDENCE_BASED_EXPERIENCE=False` at all times.
