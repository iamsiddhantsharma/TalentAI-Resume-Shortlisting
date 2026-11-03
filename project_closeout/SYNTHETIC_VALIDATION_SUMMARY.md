# TalentAI — Synthetic Validation Summary Report

**Project:** TalentAI — AI Resume Shortlister  
**Document:** Synthetic Validation Summary (`project_closeout/SYNTHETIC_VALIDATION_SUMMARY.md`)  
**Date:** 2026-10-31  
**Source Stage Reports:**  
- Stage 5E.2.3.4 Isolated Pilot Verification ([stage_5e2_3_4_final_verification_report.md](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/stage_5e2_3_4_final_verification_report.md))  
- Stage 5E.3.3 Broad Synthetic Execution Report ([stage_5e3_3_broad_synthetic_execution_report.md](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/stage_5e3_3_broad_synthetic_execution_report.md))  
**Evaluation Scope:** 100% In-Memory Synthetic Fixtures ONLY  
**Safety Invariant:** Zero real resumes, candidate files, or PII accessed. Feature flag `USE_EVIDENCE_BASED_EXPERIENCE=False` strictly preserved.

---

## 1. Important Disclaimers & Evidentiary Classification

> [!WARNING]
> **Synthetic Benchmark Limitations — Not Proof of Real-World Validity or Fairness**  
> All metrics, counts, and findings documented in this report are derived exclusively from **in-memory synthetic test fixtures** generated using standardized archetypes.  
> - **Not Real-World Performance:** Synthetic candidates have clean formatting, deterministic dates, and clear technical competencies. They do not exhibit the linguistic ambiguity, OCR errors, non-standard chronology, or structural noise of real resumes.
> - **Not Proof of Employment Fairness:** Superior Information Retrieval metrics (P@K, NDCG@K, $\rho$) measure mathematical alignment with engineer-authored rubrics. They do **not** establish absence of demographic bias, workplace fairness, or validity for real hiring decisions.
> - **Evidentiary Status:** Metrics below represent **reported benchmark outcomes** captured during the execution of authorized test harnesses (`test_stage_5e2_pilot.py` and `fixtures_broad.py`).

---

## 2. Overview of Evaluated Synthetic Cohorts

Validation was conducted in two progressive phases: the Narrow Pilot (Stage 5E.2) and the Broad Synthetic Suite (Stage 5E.3).

### 2.1 Narrow Pilot Cohort (Stage 5E.2)
- **Job Descriptions:** 3 synthetic JDs (`JD-01: Senior Backend`, `JD-02: Cloud Architect`, `JD-03: ML Engineer`).
- **Candidates:** 24 synthetic candidate profiles categorized into 4 test groups:
  - *Group A (Anchor & Regression):* High-experience profiles testing Component A–C invariance.
  - *Group B (Scoring Edge Cases):* Missing dates, inverted dates, multi-role max, zero-filling, and duration saturation.
  - *Group C (Duration Pooling):* Time-sliced overlapping roles, non-overlapping intervals, and concurrent tenures.
  - *Group D (IR Evaluation):* 12 ranked profiles with adjudicated human ground truth.
- **Test Result:** 26/26 unit tests passed in 0.031s (Stage 5E.2.3.4).

### 2.2 Broad Synthetic Suite Cohort (Stage 5E.3)
- **Scale:** 12 Job Descriptions, 240 synthetic candidate profiles (exactly 20 candidates per JD cohort).
- **Technical Strata Coverage (6 Job Families):**
  1. *Backend & Distributed Systems* (`JD-BROAD-01`, `JD-BROAD-02`)
  2. *Frontend, Mobile & Full-Stack* (`JD-BROAD-03`, `JD-BROAD-04`)
  3. *AI, Machine Learning & Data* (`JD-BROAD-05`, `JD-BROAD-06`)
  4. *DevOps, SRE & Cloud Infrastructure* (`JD-BROAD-07`, `JD-BROAD-08`)
  5. *Security & Systems Engineering* (`JD-BROAD-09`, `JD-BROAD-10`)
  6. *Quality & Engineering Leadership* (`JD-BROAD-11`, `JD-BROAD-12`)
- **Experience Paradigms Represented:**
  - *Case 1 (Bounded):* 5 JDs (`JD-BROAD-01, 04, 06, 07, 10`)
  - *Case 2 (Minimum-Only):* 4 JDs (`JD-BROAD-03, 05, 09, 11`)
  - *Case 3 (Maximum-Only):* 1 JD (`JD-BROAD-02`)
  - *Case 4 (G1-C Unbounded):* 2 JDs (`JD-BROAD-08, 12`)
- **Ground-Truth Label Distribution (240 Candidates):**
  - Grade 3 (Exceptional Fit): 74 candidates (30.8%)
  - Grade 2 (Good / Partial Fit): 108 candidates (45.0%)
  - Grade 1 (Marginal Fit): 46 candidates (19.2%)
  - Grade 0 (Unqualified): 12 candidates (5.0%)
  - *Total Relevant ($Grade \ge 2$):* $R = 182$ candidates (15 per cohort in 10 cohorts; 16 in 2 cohorts)
  - *Total Non-Relevant ($Grade \le 1$):* $NR = 58$ candidates

---

## 3. Macro-Average Benchmark Results (Stage 5E.3.3)

All 240 candidates across all 12 JDs were scored independently through `RankingEngine(use_evidence_based_experience=False)` (Legacy Categorical Engine) and `RankingEngine(use_evidence_based_experience=True)` (Evidence-Based Engine). Metrics were computed using the verified pilot evaluation harness ([tests/pilot/metrics.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/metrics.py)).

| Evaluation Metric | Evidence-Based Engine | Legacy Categorical Engine | Absolute Delta ($\Delta$) | Relative Improvement | Stage 5E.3.1 Advisory Target | Target Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Precision@3 (Macro Avg)** | **1.0000** | 0.9445 | **+0.0555** | **+5.88%** | $\ge 0.85$ | **Met Target (+15.0%)** |
| **Precision@5 (Macro Avg)** | **1.0000** | 0.9667 | **+0.0333** | **+3.45%** | $\ge 0.75$ | **Met Target (+25.0%)** |
| **Recall@3 (Exhaustive Denom)** | **0.1979** | 0.1868 | **+0.0111** | **+5.94%** | $\ge 0.18$ | **Met Target (+1.79%)** |
| **Recall@5 (Exhaustive Denom)** | **0.3298** | 0.3187 | **+0.0111** | **+3.48%** | $\ge 0.30$ | **Met Target (+2.98%)** |
| **NDCG@3 (Macro Avg)** | **1.0000** | 0.9441 | **+0.0559** | **+5.92%** | $\ge 0.85$ | **Met Target (+15.0%)** |
| **NDCG@5 (Macro Avg)** | **1.0000** | 0.9596 | **+0.0404** | **+4.21%** | $\ge 0.82$ | **Met Target (+18.0%)** |
| **Spearman Rank Correlation ($\rho$)** | **0.9156** | 0.8404 | **+0.0751** | **+8.94%** | $\ge 0.75$ | **Met Target (+16.56%)** |
| **Top-5 Shortlist Tie Rate** | **0.1833** | 0.4000 | **-0.2167** | **-54.18%** | $\le 0.05$ (Non-Unbounded) | **Analyzed Below** |
| **Full Cohort Tie Rate** | **0.0272** | 0.0719 | **-0.0447** | **-62.17%** | N/A | **62.2% Reduction** |
| **Component A–C Invariance** | **0 violations** | 0 | **0.0000** | Exact Match | $\Delta_{\text{max}} = 0.0000$ | **Met Target (Exact)** |
| **Component D Attribution Residual** | **0.0100** | N/A | $\le 0.0100$ | Rounding Exact | $\le 0.0100$ | **Met Target (Exact)** |

*Note: All targets from Stage 5E.3.1 are advisory engineering guidelines, not binding production release gates.*

---

## 4. Granular Per-JD Evaluation Breakdown

The table below records the per-cohort performance across all 12 Job Descriptions:

| JD ID | Job Family & Stratum | Paradigm | Target ($Y$) | Denom ($R$) | P@3 (Ev / Leg) | P@5 (Ev / Leg) | NDCG@3 (Ev / Leg) | NDCG@5 (Ev / Leg) | Spearman $\rho$ (Ev / Leg) | Top-5 Ties (Ev / Leg) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`JD-BROAD-01`** | Backend & Distributed Systems | Bounded | 8.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-02`** | Backend & Distributed Systems | Max-Only | 4.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-03`** | Frontend, Mobile & Full-Stack | Min-Only | 5.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-04`** | Frontend, Mobile & Full-Stack | Bounded | 6.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-05`** | AI, Machine Learning & Data | Min-Only | 4.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-06`** | AI, Machine Learning & Data | Bounded | 7.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-07`** | DevOps, SRE & Cloud Infra | Bounded | 7.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-08`** | DevOps, SRE & Cloud Infra | Unbounded | None | 16 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.8753** / 0.8848 | **0.600** / 0.600 |
| **`JD-BROAD-09`** | Security & Systems Engineering | Min-Only | 4.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 0.732 | **1.000** / 0.806 | **0.9154** / 0.7950 | **0.100** / 0.300 |
| **`JD-BROAD-10`** | Security & Systems Engineering | Bounded | 5.0y | 15 | **1.00** / 0.67 | **1.00** / 0.80 | **1.000** / 0.799 | **1.000** / 0.855 | **0.9201** / 0.7104 | **0.100** / 0.600 |
| **`JD-BROAD-11`** | Quality & Engineering Leadership | Min-Only | 3.0y | 15 | **1.00** / 0.67 | **1.00** / 0.80 | **1.000** / 0.799 | **1.000** / 0.855 | **0.9201** / 0.7104 | **0.100** / 0.600 |
| **`JD-BROAD-12`** | Quality & Engineering Leadership | Unbounded | None | 16 | **1.00** / 1.00 | **1.00** / 1.00 | **1.000** / 1.000 | **1.000** / 1.000 | **0.8753** / 0.8848 | **0.600** / 0.600 |

---

## 5. Critical Algorithmic Insights from Synthetic Testing

### 5.1 Elimination of Single-Domain Precision Collapse
The most significant finding of broad synthetic validation occurred in single-domain cohorts (`JD-BROAD-10: Embedded Systems` and `JD-BROAD-11: SDET Automation`, $M=1$):
- **Legacy Engine Failure:** Legacy categorical scoring suffered severe precision collapse, dropping to **Precision@3 = 0.6667** (1 out of every 3 top candidates was non-relevant) and **NDCG@3 = 0.7989**.
- **Root Cause:** Legacy scoring relied on uncalibrated keyword overlap. Candidates who matched peripheral generic skills (e.g., Git, Linux) received high scores despite zero verified tenure in embedded systems or test automation.
- **Evidence-Based Resolution:** The Evidence Engine maintained **Precision@3 = 1.0000** and **NDCG@3 = 1.0000** by multiplying semantic relevance by verified duration ($E = 100 \times S_{\text{agg}} \times D$), suppressing unqualified candidates with shallow or unverified domain experience.

### 5.2 Deterministic Tie Resolution
- **Legacy Tie Clustering:** The legacy engine assigns discrete categorical scores ($0, 40, 70, 100$) to experience, resulting in a high Top-5 tie rate of **0.4000** (40% of candidate pairs in the top 5 tied in score).
- **Evidence Tie Reduction:** The continuous evidence formula ($E = 100 \times S_{\text{agg}} \times D$) reduced the Top-5 tie rate to **0.1833** overall (-54.2%).
- **Non-Unbounded Performance:** In the 10 non-unbounded JDs, the Top-5 tie rate was reduced to **0.1000** (exactly 1 tied pair, which is the intentional Twin Stability pair Candidates #19 & #20 who share identical resumes). Outside the twin pair, **zero score ties occurred in the top 5**.
- **G1-C Unbounded Cohorts:** In `JD-BROAD-08` and `JD-BROAD-12`, all candidates receive $D=0.000, E=0.00$ per the Gate 1 Rule C duration zeroing safeguard. Candidates with identical Component A–C scores naturally tied, producing an expected tie rate of 0.6000. This is an intentional safeguard behavior, not an engine defect.

### 5.3 Diagnostic & Edge-Case Safeguards
All 8 edge-case behaviors passed static and runtime assertions:
1. **Saturation ($D=1.000$):** Candidates with tenure $\ge Y_{\text{target}}$ received full duration credit without score inflation beyond 1.000.
2. **Proportional Damping ($0 < D < 1$):** Candidates with tenure $< Y_{\text{target}}$ scaled linearly with verified duration ratio.
3. **Rule 10 Zeroing:** Candidates with zero relevant domain experience received strictly $E = 0.00$ with diagnostic note `no_relevant_experience`.
4. **Missing Dates Safeguard:** Profiles with missing date fields received strictly $D = 0.000, E = 0.00$ with diagnostic note `missing_dates`.
5. **Inverted Dates Safeguard:** Profiles with start dates chronologically after end dates received strictly $D = 0.000, E = 0.00$ with diagnostic note `invalid_date_range`.
6. **Concurrent Duration Pooling:** Overlapping roles were consolidated via time-sliced intervals, preventing double-counting of simultaneous tenures.

---

## 6. Summary Conclusion

The synthetic validation program successfully proved the algorithmic superiority, mathematical stability, and regression invariance of the Evidence-Based Experience Ranking Engine within the synthetic domain. 

However, because these evaluations were performed exclusively on synthetic fixtures, they cannot substitute for authorized shadow evaluation on real resumes. The feature flag `USE_EVIDENCE_BASED_EXPERIENCE = False` remains strictly enforced.
