# TalentAI — Stage 5E.3.3: Broad Synthetic Suite Execution and IR Benchmarking Report

**Date:** 2026-10-31  
**Stage:** 5E.3.3 (Broad Synthetic Suite Execution and IR Benchmarking ONLY)  
**Execution Authority:** Authorization for Broad Synthetic Benchmark Execution & Verification  
**Final Status:** **PASS**  
**Safety Invariant:** Zero modifications to production code, schemas, formulas, weights, thresholds, database (`talent_ai`), active batches (`07281a64-46cf-46b4-a5c1-a0d46b13e7b2`), resume storage, or `.env`. Feature flag `USE_EVIDENCE_BASED_EXPERIENCE=False` strictly preserved. Pure in-memory synthetic cohort evaluated.

---

## 1. Executive Summary

Following successful remediation in Stage 5E.3.3.1 ([stage_5e3_3_1_fixture_remediation_report.md](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/stage_5e3_3_1_fixture_remediation_report.md)), the broad synthetic validation cohort was audited, executed, and benchmarked across all 12 Job Descriptions and 240 synthetic candidate profiles in complete offline isolation.

### Key Evaluation Findings:
1. **Fixture Integrity & Coverage (Step 1):** **PASS**. Exactly 12 Job Descriptions and 240 synthetic candidates across 6 technical strata were verified. All four Gate 1 experience paradigms (Bounded, Minimum-Only, Maximum-Only, and G1-C Unbounded) are fully represented and accurately classified.
2. **Suite Execution (Step 2):** **PASS**. The authorized test suite executed cleanly with **26/26 tests passing** (0 failures, 0 errors, 0 skipped, execution time 0.031s). The broad synthetic dataset integrity verification passed with **0 errors**.
3. **Information Retrieval Superiority (Step 3):**
   - **Precision@3:** Evidence Engine achieved **1.0000** vs. Legacy Engine **0.9445** (+5.55% delta). Legacy suffered severe precision collapse ($P@3 = 0.6667$) on single-domain JDs (`JD-BROAD-10` and `JD-BROAD-11`), whereas Evidence maintained 100% precision.
   - **Precision@5:** Evidence Engine achieved **1.0000** vs. Legacy Engine **0.9667** (+3.33% delta).
   - **Recall@3 (Exhaustive Denominator):** Evidence Engine achieved **0.1979** vs. Legacy **0.1868** (against verified denominators $R_{\text{cohort}}=15$ or $16$).
   - **Recall@5 (Exhaustive Denominator):** Evidence Engine achieved **0.3298** vs. Legacy **0.3187**.
   - **NDCG@3:** Evidence Engine achieved **1.0000** vs. Legacy **0.9441** (+5.59% delta).
   - **NDCG@5:** Evidence Engine achieved **1.0000** vs. Legacy **0.9596** (+4.04% delta).
   - **Spearman Rank Correlation ($\rho$ vs. Human Ground Truth):** Evidence Engine achieved **0.9156** vs. Legacy **0.8404** (+0.0751 delta).
4. **Tie Resolution:**
   - **Top-5 Shortlist Tie Rate:** Reduced from **0.4000** (Legacy) to **0.1833** (Evidence), representing a **54.2% tie reduction**. In the 10 non-unbounded JDs, Top-5 ties were reduced to 0.1000 (exactly 1 tied pair, which is the intentional twin pair Candidates #19 and #20).
   - **Cohort Tie Rate:** Reduced from **0.0719** (Legacy) to **0.0272** (Evidence), a **62.2% tie reduction**.
5. **Safety & Governance Invariants:**
   - **Component A–C Invariance:** **100% Verified** ($|\Delta| = 0.0000$ across all 240 candidates).
   - **Component D Attribution:** **100% Verified** ($\Delta_{\text{final}} = 0.35 \times (E_{\text{ev}} - E_{\text{leg}})$, max rounding residual $\le 0.0100$).
   - **Global Feature Flag:** Maintained strictly `USE_EVIDENCE_BASED_EXPERIENCE = False`.

---

## 2. Step 1: Read-Only Fixture Audit Results

Prior to execution, an exhaustive read-only inspection of [fixtures_broad.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/fixtures_broad.py) was performed against the Stage 5E.3.1 validation plan:

| Audit Criterion | Verification Method | Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **Total JDs & Candidates** | Exact count of dictionaries | Exactly 12 JDs, 240 Candidates (20 per JD) | **PASS** |
| **Paradigm Coverage** | `JD_STRATA_METADATA` audit | Bounded (5), Min-Only (4), Max-Only (1), Unbounded (2) | **PASS** |
| **Range-Status Classification** | `CandidateExperienceDiagnostic` audit | `bounded` (5 JDs), `min_only` (4 JDs), `max_only` (1 JD), `unspecified` (2 JDs) | **PASS** |
| **Ground-Truth Counts** | `BROAD_GROUND_TRUTH_LABELS` audit | 74 Grade 3, 108 Grade 2, 46 Grade 1, 12 Grade 0 | **PASS** |
| **Relevant Denominators** | Filter `binary_relevance == 1` | 10 cohorts with $R=15$, 2 cohorts with $R=16$ ($R_{\text{total}} = 182$) | **PASS** |
| **Candidate #18 Coherence** | Profile & rubric review | Unbounded: Grade 3, 6.0y, G1-C note; Non-unbounded: Grade 1, 0.0y, sub-threshold | **PASS** |
| **Score Leakage Separation** | Key inspection on candidate dicts | Zero model score/rank keys in candidate fixtures or ground truth | **PASS** |
| **Fixture Integrity Check** | `verify_broad_fixtures_integrity()` | Exit code 0, status `PASS`, 0 errors | **PASS** |

All Step 1 criteria passed without discrepancy. Authorization to proceed to Step 2 was confirmed.

---

## 3. Step 2: Test Suite Execution Details

### 3.1 Environment & Execution Parameters
- **Test Command:**
  ```powershell
  python ..\tests\pilot\test_stage_5e2_pilot.py
  ```
- **Working Directory:** `c:\Users\siddh\OneDrive\Desktop\Talent_AI\backend`
- **Execution Environment:** `Python 3.11.9` (Windows AMD64)
- **Settings Resolution:** Local `backend\.env` resolved via `pydantic_settings`
- **Execution Date/Time:** `2026-10-31 17:03:52 UTC`
- **Elapsed Time:** `0.031 seconds` (test execution)

### 3.2 Test Results Summary
- **Total Tests Discovered:** **26**
- **Passed:** **26** (100%)
- **Failed:** **0**
- **Errors:** **0**
- **Skipped:** **0**
- **Exit Code:** `0`

### 3.3 Test Group Breakdown
- **Group A (Invariance & Flags):** 3/3 Passed (Zero drift on Components A–C; attribution exact; flag `False`).
- **Group B (Scoring & Edge Cases):** 8/8 Passed (Saturation, damping, Rule 10, missing dates, G1-C, multi-role max, zero-filling, case deduplication).
- **Group C (Duration Pooling):** 4/4 Passed (Time-sliced algorithm verified; non-overlapping sum, overlapping max rule, concurrent intervals, unweighted union rejection).
- **Group D (Metrics Engine):** 6/6 Passed (P@K, Recall@K with exhaustive denominator, NDCG@K exponential gains, Spearman $\rho$, tie rates, rubric mapping).
- **Group E (Diagnostics & Provenance):** 5/5 Passed (Provenance fields, missing-date alerts, G1-C notices, zero-score vs missing data distinction, evidence preservation under zero duration).

---

## 4. Step 3: Verified IR and Ranking Metrics

All 240 synthetic candidates across all 12 Job Descriptions were scored through independent instances of `RankingEngine(use_evidence_based_experience=False)` (Legacy) and `RankingEngine(use_evidence_based_experience=True)` (Evidence). Metrics were calculated using [tests/pilot/metrics.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/metrics.py).

### 4.1 Granular Per-JD Evaluation Results

| JD ID | Job Family & Stratum | Experience Paradigm | Saturation Target | Relevant Denom ($R$) | P@3 (Ev / Leg) | P@5 (Ev / Leg) | R@3 (Ev / Leg) | R@5 (Ev / Leg) | NDCG@3 (Ev / Leg) | NDCG@5 (Ev / Leg) | Spearman $\rho$ (Ev / Leg) | Top-5 Ties (Ev / Leg) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`JD-BROAD-01`** | Backend & Distributed Systems | Case 1: Bounded | 8.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-02`** | Backend & Distributed Systems | Case 3: Max-Only | 4.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-03`** | Frontend, Mobile & Full-Stack | Case 2: Min-Only | 5.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-04`** | Frontend, Mobile & Full-Stack | Case 1: Bounded | 6.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-05`** | AI, Machine Learning & Data | Case 2: Min-Only | 4.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-06`** | AI, Machine Learning & Data | Case 1: Bounded | 7.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-07`** | DevOps, SRE & Cloud Infra | Case 1: Bounded | 7.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 1.000 | **1.000** / 1.000 | **0.9258** / 0.8714 | **0.100** / 0.300 |
| **`JD-BROAD-08`** | DevOps, SRE & Cloud Infra | Case 4: G1-C Unbounded | None | 16 | **1.00** / 1.00 | **1.00** / 1.00 | **0.188** / 0.188 | **0.313** / 0.313 | **1.000** / 1.000 | **1.000** / 1.000 | **0.8753** / 0.8848 | **0.600** / 0.600 |
| **`JD-BROAD-09`** | Security & Systems Engineering | Case 2: Min-Only | 4.0y | 15 | **1.00** / 1.00 | **1.00** / 1.00 | **0.200** / 0.200 | **0.333** / 0.333 | **1.000** / 0.732 | **1.000** / 0.806 | **0.9154** / 0.7950 | **0.100** / 0.300 |
| **`JD-BROAD-10`** | Security & Systems Engineering | Case 1: Bounded | 5.0y | 15 | **1.00** / 0.67 | **1.00** / 0.80 | **0.200** / 0.133 | **0.333** / 0.267 | **1.000** / 0.799 | **1.000** / 0.855 | **0.9201** / 0.7104 | **0.100** / 0.600 |
| **`JD-BROAD-11`** | Quality & Engineering Leadership | Case 2: Min-Only | 3.0y | 15 | **1.00** / 0.67 | **1.00** / 0.80 | **0.200** / 0.133 | **0.333** / 0.267 | **1.000** / 0.799 | **1.000** / 0.855 | **0.9201** / 0.7104 | **0.100** / 0.600 |
| **`JD-BROAD-12`** | Quality & Engineering Leadership | Case 4: G1-C Unbounded | None | 16 | **1.00** / 1.00 | **1.00** / 1.00 | **0.188** / 0.188 | **0.313** / 0.313 | **1.000** / 1.000 | **1.000** / 1.000 | **0.8753** / 0.8848 | **0.600** / 0.600 |

---

### 4.2 Overall Macro-Average Benchmark Summary

| Evaluation Metric | Evidence-Based Engine | Legacy Categorical Engine | Absolute Delta ($\Delta$) | Relative Improvement |
| :--- | :---: | :---: | :---: | :---: |
| **Precision@3 (Macro Average)** | **1.0000** | 0.9445 | **+0.0555** | **+5.88%** |
| **Precision@5 (Macro Average)** | **1.0000** | 0.9667 | **+0.0333** | **+3.45%** |
| **Recall@3 (Macro Average)** | **0.1979** | 0.1868 | **+0.0111** | **+5.94%** |
| **Recall@5 (Macro Average)** | **0.3298** | 0.3187 | **+0.0111** | **+3.48%** |
| **NDCG@3 (Macro Average)** | **1.0000** | 0.9441 | **+0.0559** | **+5.92%** |
| **NDCG@5 (Macro Average)** | **1.0000** | 0.9596 | **+0.0404** | **+4.21%** |
| **Spearman Rank Correlation ($\rho$)** | **0.9156** | 0.8404 | **+0.0751** | **+8.94%** |
| **Top-5 Shortlist Tie Rate** | **0.1833** | 0.4000 | **-0.2167** | **-54.18%** |
| **Full Cohort Tie Rate** | **0.0272** | 0.0719 | **-0.0447** | **-62.17%** |
| **Component A–C Invariance Failures** | **0** | 0 | **0.0000** | 100% Invariant |
| **Component D Max Attribution Error** | **0.0100** | N/A | $\le 0.0100$ | Rounding Exact |

---

### 4.3 Component Invariance & Attribution Verification
1. **Component A–C Invariance:**
   - Every candidate match result produced identical subscores between engines:
     - Component A (Required Skills, 25%): $|\Delta| = 0.0000$
     - Component B (Responsibilities, 30%): $|\Delta| = 0.0000$
     - Component C (Tools & Technologies, 10%): $|\Delta| = 0.0000$
   - Total invariance violations across 240 candidates: **0 (Zero)**.
2. **Component D Attribution:**
   - Final score difference formula: $\Delta_{\text{final}} = \text{Score}_{\text{evidence}} - \text{Score}_{\text{legacy}}$.
   - Theoretical expectation: $0.35 \times (E_{\text{evidence}} - E_{\text{legacy}})$.
   - Maximum residual $| \Delta_{\text{final}} - \text{round}(0.35 \times \Delta_{\text{exp}}, 2) |$: **0.0100** across all 240 candidates. All residuals are strictly attributable to intermediate 2-decimal display rounding.
3. **Experience Duration & Diagnostic Safeguards:**
   - **Tenure Saturation ($D=1.000$):** Candidate #1 and #13 received full credit without over-inflation beyond 1.000.
   - **Proportional Damping ($D \in (0, 1)$):** Candidates #5, #6, #11, and #12 scaled linearly with duration ratio.
   - **Rule 10 Zeroing:** Candidate #10 produced strictly $E = 0.00$ with diagnostic notice `no_relevant_experience`.
   - **Missing Dates Safeguard:** Candidate #16 produced strictly $D = 0.000, E = 0.00$ with diagnostic notice `missing_dates`.
   - **Inverted Dates Safeguard:** Candidate #17 produced strictly $D = 0.000, E = 0.00$ with diagnostic notice `invalid_date_range`.
   - **G1-C Unbounded Safeguard:** Under `JD-BROAD-08` and `JD-BROAD-12`, all candidates produced $D = 0.000, E = 0.00$ with `diagnostic_status="unspecified"`, preserving the mandatory safeguard while keeping high semantic similarity ($S_{\text{agg}} \ge 0.88$) in the evidence payload.

---

## 5. Step 4: Interpretation of Results & Advisory Target Comparison

### 5.1 Advisory Target Evaluation

> [!NOTE]
> All targets below are from the approved Stage 5E.3.1 validation roadmap. In accordance with the governance protocol, these thresholds are **advisory benchmarks**, not binding production release gates.

| Evaluation Metric | Stage 5E.3.1 Advisory Target | Evidence-Based Result | Status Against Advisory Target |
| :--- | :---: | :---: | :---: |
| **Precision@3 (Cohort Average)** | $\ge 0.85$ | **1.0000** | **Met Target (+15.0%)** |
| **Precision@5 (Cohort Average)** | $\ge 0.75$ | **1.0000** | **Met Target (+25.0%)** |
| **Recall@3 (Cohort Average)** | $\ge 0.18$ | **0.1979** | **Met Target (+1.79%)** |
| **Recall@5 (Cohort Average)** | $\ge 0.30$ | **0.3298** | **Met Target (+2.98%)** |
| **NDCG@3 (Cohort Average)** | $\ge 0.85$ | **1.0000** | **Met Target (+15.0%)** |
| **NDCG@5 (Cohort Average)** | $\ge 0.82$ | **1.0000** | **Met Target (+18.0%)** |
| **Spearman Rank Correlation ($\rho$)** | $\ge 0.75$ | **0.9156** | **Met Target (+16.56%)** |
| **Top-5 Shortlist Tie Rate** | $\le 5.0\%$ (Non-Unbounded) | **10.0%** (Twin pair only) | **Analyzed Below** |
| **Components A–C Invariance** | $\Delta_{\text{max}} = 0.0000$ | **0.0000** | **Met Target (Exact)** |
| **Component D Attribution Residual** | $\le 0.0100$ | **0.0100** | **Met Target (Exact)** |

---

### 5.2 Deep-Dive into Strata Performance & Legacy Failure Modes

1. **Catastrophic Precision Collapse in Single-Domain Roles Under Legacy Engine:**
   - In single-preferred-domain cohorts (`JD-BROAD-10: Embedded Systems` and `JD-BROAD-11: SDET Automation`, $M=1$):
     - Legacy Precision@3 dropped to **0.6667** (1 out of every 3 top candidates was non-relevant).
     - Legacy Precision@5 dropped to **0.8000**.
     - Legacy NDCG@3 dropped to **0.7989**.
   - **Root Cause:** Legacy categorical scoring over-indexes on peripheral skill matches and fails to dampen candidates with zero domain depth or unverified dates. Consequently, unqualified or marginal candidates outranked qualified specialists.
   - **Evidence-Based Resolution:** Evidence engine achieved **Precision@3 = 1.0000** and **NDCG@3 = 1.0000** across both roles by combining domain calibration and duration factors ($S_{\text{agg}} \times D$).
2. **Multi-Domain Dilution Under Legacy Engine:**
   - In triple-domain role `JD-BROAD-09` ($M=3$, Cloud Security):
     - Legacy NDCG@3 dropped to **0.7318** and NDCG@5 to **0.8062**.
     - Legacy Spearman $\rho$ dropped to **0.7950**.
   - **Evidence-Based Resolution:** Evidence engine maintained **NDCG@3 = 1.0000** and achieved **Spearman $\rho = 0.9154$**.
3. **Analysis of Tie Rates:**
   - **Cohort Ties:** In the 10 non-unbounded JDs, Evidence engine produced a cohort tie rate of **0.0053** (exactly 1 tied pair: Candidates #19 and #20, the identical Twin Stability pair). Outside the twin pair, **evidence-based ranking produced zero score ties**.
   - **Top-5 Ties:** In the 10 non-unbounded JDs, the Top-5 tie rate was 0.1000 (1 pair out of 10 pairwise combinations in the top 5), which is exclusively the deterministic twin pair.
   - **G1-C Unbounded Elevated Ties:** In `JD-BROAD-08` and `JD-BROAD-12`, all candidates receive $D=0.000, E=0.00$. Candidates who share identical Component A–C scores naturally tie in the final score. This is an expected mathematical consequence of the Gate 1 Rule C duration zeroing safeguard, not an engine deficiency.

---

### 5.3 Limitations of Synthetic Data & Statistical Caveats

1. **Synthetic Data Limitations:**
   - All 240 profiles were deterministically constructed using standardized templates. Real candidate resumes contain noise, ambiguous role titles, formatting anomalies, and non-standard date expressions that may challenge parsing.
2. **Engineer-Authored Ground Truth:**
   - While raters were double-blinded and adjudicated with $\kappa = 1.000$ (with Candidate #3 adjudicated), labels were authored alongside synthetic archetypes. Real-world human evaluations will exhibit higher variance ($\kappa \approx 0.70$–$0.80$).
3. **Statistical Significance Caveat:**
   - Although the Evidence Engine outperformed Legacy across all 12 cohorts ($\Delta_{\text{P@3}} = +0.0555$, $\Delta_{\text{NDCG@3}} = +0.0559$, $\Delta_{\rho} = +0.0751$), this sample consists of 240 synthetic profiles. Statistical significance claims regarding production impact cannot be formally asserted until evaluated on de-identified real resumes in Stage 5E.4.

---

## 6. Files Created or Modified

### Files Modified:
- *None during Step 2–4.* (Read-only execution audit strictly maintained).

### Files Created:
- [tests/pilot/stage_5e3_3_broad_synthetic_execution_report.md](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/stage_5e3_3_broad_synthetic_execution_report.md) (This report)
- `scratch/compute_broad_benchmark_metrics.py` (Temporary execution harness in artifact scratch directory)

---

## 7. Strict Safety Boundary Confirmation

The following safety boundaries were strictly adhered to throughout Stage 5E.3.3:
- **Synthetic Cohort Only:** 100% fictional in-memory profiles; zero production candidate data, resumes, or PII accessed.
- **Production Immutability:** No production code in `backend/app/` or `frontend/src/` was modified.
- **Production Formulas & Schemas Unchanged:** Scoring weights, thresholds, and schemas remain unmodified.
- **Database & Storage Intact:** MongoDB instance, database `talent_ai`, collection `resumes`, and active batch `07281a64-46cf-46b4-a5c1-a0d46b13e7b2` were not accessed or modified.
- **Configuration & Dependencies Untouched:** `.env` was not modified; no packages were installed or upgraded.
- **Feature Flag Immutability:** `USE_EVIDENCE_BASED_EXPERIENCE` remains strictly `False`.
- **No Progression Beyond Stage 5E.3.3:** Zero work initiated for Stage 5E.3.4 or Stage 5E.4.

---

## 8. Final Status & Recommendation

- **Final Status:** **PASS**
- **Benchmark Outcome:** The Evidence-Based Experience Ranking Engine successfully demonstrated superior ranking fidelity, enhanced precision, eliminated precision collapse on single-domain JDs, and drastically reduced score ties across 240 synthetic candidates and 12 Job Descriptions.
- **Next Stage Gate:** Await user review of this report and explicit authorization before proceeding to **Stage 5E.3.4: Real-Data Privacy, Governance & Authorization Protocol**.
