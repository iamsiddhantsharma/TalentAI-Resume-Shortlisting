# TalentAI — Stage 5E.3.2: Construction of Broad Synthetic Cohort Report

**Date:** 2026-10-31  
**Stage:** 5E.3.2 (Construction of Broad Synthetic Cohort ONLY)  
**Execution Authority:** Authorization for In-Memory Synthetic Fixture Construction ONLY  
**Safety Invariant:** Zero modifications to production code, schemas, formulas, weights, database, active batches, `.env`, or feature flag (`USE_EVIDENCE_BASED_EXPERIENCE=False`). Zero test execution or metric calculation occurred.

---

## 1. Executive Summary & Deliverables

In accordance with the approved Stage 5E.3.1 validation roadmap ([stage_5e3_1_broader_validation_plan.md](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/stage_5e3_1_broader_validation_plan.md)), the broad synthetic validation dataset has been successfully constructed in:
**[tests/pilot/fixtures_broad.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/fixtures_broad.py)**

### Key Cohort Dimensions:
- **Total Job Descriptions:** **12** across **6 distinct technical strata**
- **Total Synthetic Candidates:** **240** (exactly **20 candidates per JD cohort**)
- **Total Independent Ground-Truth Labels:** **240** (stored strictly separate from candidate profile objects)
- **Zero Model Score Leakage:** Candidate profiles contain only candidate input data; expected scores and internal ranking results are completely excluded from ground-truth fixtures.
- **Integrity Status:** **PASS** (100% structural verification via `verify_broad_fixtures_integrity()`, zero errors).

---

## 2. Cohort Distribution Across JDs & Job Families

The 240 synthetic profiles and 12 Job Descriptions span 6 major technical disciplines:

| Stratum # | Technical Discipline / Job Family | Job Description ID & Role Title | Experience Range Paradigm & Target | Preferred Domains ($M$) | Candidate ID Range |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **Stratum 1** | **Backend & Distributed Systems** | **JD-BROAD-01:** Principal Distributed Backend Engineer | Case 1: Bounded (4.0–8.0y, $Y_{\text{target}}=8.0\text{y}$) | Distributed Storage, Consensus Systems ($M=2$) | `BCAND-001` to `BCAND-020` |
| | | **JD-BROAD-02:** Mid-Level Microservices Platform Engineer | Case 3: Max-Only ($\le 4.0\text{y}$, $Y_{\text{target}}=4.0\text{y}$) | REST APIs, Event-Driven Architecture ($M=2$) | `BCAND-021` to `BCAND-040` |
| **Stratum 2** | **Frontend, Mobile & Full-Stack** | **JD-BROAD-03:** Lead React / Next.js Web Architect | Case 2: Min-Only ($\ge 5.0\text{y}$, $Y_{\text{target}}=5.0\text{y}$) | Modern Web Platforms, Frontend Performance ($M=2$) | `BCAND-041` to `BCAND-060` |
| | | **JD-BROAD-04:** Senior iOS Systems Engineer | Case 1: Bounded (3.0–6.0y, $Y_{\text{target}}=6.0\text{y}$) | iOS Frameworks, SwiftUI / Concurrency ($M=2$) | `BCAND-061` to `BCAND-080` |
| **Stratum 3** | **AI, Machine Learning & Data** | **JD-BROAD-05:** Senior MLOps & LLM Platform Engineer | Case 2: Min-Only ($\ge 4.0\text{y}$, $Y_{\text{target}}=4.0\text{y}$) | Model Serving, LLMOps / Orchestration ($M=2$) | `BCAND-081` to `BCAND-100` |
| | | **JD-BROAD-06:** Real-Time Data Infrastructure Engineer | Case 1: Bounded (3.0–7.0y, $Y_{\text{target}}=7.0\text{y}$) | Apache Spark, Real-Time Lakehouse ($M=2$) | `BCAND-101` to `BCAND-120` |
| **Stratum 4** | **DevOps, SRE & Cloud Infra** | **JD-BROAD-07:** Staff Site Reliability Engineer | Case 1: Bounded (4.0–7.0y, $Y_{\text{target}}=7.0\text{y}$) | Incident Management, Cloud Observability ($M=2$) | `BCAND-121` to `BCAND-140` |
| | | **JD-BROAD-08:** Cloud Infrastructure Architect | Case 4: G1-C Unbounded ($Y_{\text{target}}=\text{None}$) | Multi-Cloud Architecture, IaC ($M=2$) | `BCAND-141` to `BCAND-160` |
| **Stratum 5** | **Security & Systems Engineering** | **JD-BROAD-09:** Senior Cloud Security & DevSecOps Engineer | Case 2: Min-Only ($\ge 4.0\text{y}$, $Y_{\text{target}}=4.0\text{y}$) | Zero Trust, Cloud IAM, DevSecOps ($M=3$) | `BCAND-161` to `BCAND-180` |
| | | **JD-BROAD-10:** Embedded Systems & Firmware Engineer | Case 1: Bounded (3.0–5.0y, $Y_{\text{target}}=5.0\text{y}$) | Real-Time Operating Systems (RTOS) ($M=1$) | `BCAND-181` to `BCAND-200` |
| **Stratum 6** | **Quality & Engineering Leadership** | **JD-BROAD-11:** Staff Software Engineer in Test (SDET) | Case 2: Min-Only ($\ge 3.0\text{y}$, $Y_{\text{target}}=3.0\text{y}$) | Automated Test Frameworks ($M=1$) | `BCAND-201` to `BCAND-220` |
| | | **JD-BROAD-12:** Technical Engineering Lead | Case 4: G1-C Unbounded ($Y_{\text{target}}=\text{None}$) | Delivery Leadership, Systems Architecture ($M=2$) | `BCAND-221` to `BCAND-240` |

---

## 3. Experience-Range Paradigm Coverage

All approved Gate 1 experience paradigms are systematically evaluated across the 12 JDs:

1. **Case 1: Bounded Ranges ($Y_{\text{min}} > 0, Y_{\text{max}} > 0 \implies Y_{\text{target}} = Y_{\text{max}}$):**
   - 5 Job Descriptions: `JD-BROAD-01`, `04`, `06`, `07`, `10`.
   - Evaluates duration factor $D = \min(1.0, Y_{\text{actual}} / Y_{\text{max}})$ across targets from 5.0 years to 8.0 years.
2. **Case 2: Minimum-Only Ranges ($Y_{\text{min}} > 0, Y_{\text{max}} = \text{None} \implies Y_{\text{target}} = Y_{\text{min}}$):**
   - 4 Job Descriptions: `JD-BROAD-03`, `05`, `09`, `11`.
   - Evaluates duration factor $D = \min(1.0, Y_{\text{actual}} / Y_{\text{min}})$ across floor targets from 3.0 years to 5.0 years.
3. **Case 3: Maximum-Only Ranges ($Y_{\text{min}} = \text{None}, Y_{\text{max}} > 0 \implies Y_{\text{target}} = Y_{\text{max}}$):**
   - 1 Job Description: `JD-BROAD-02`.
   - Evaluates duration factor $D = \min(1.0, Y_{\text{actual}} / Y_{\text{max}})$ across ceiling target of 4.0 years.
4. **Case 4: Gate 1 Rule C Unbounded Ranges ($\text{Min} = \text{None}, \text{Max} = \text{None}$):**
   - 2 Job Descriptions: `JD-BROAD-08`, `12`.
   - Evaluates mandatory duration zeroing ($D = 0.000, E = 0.00$) with diagnostic status `"unspecified"` and `range_status="unspecified"`.
5. **Preferred Domain Cardinalities ($M$):**
   - Single-domain JDs ($M=1$): `JD-BROAD-10`, `11`.
   - Dual-domain JDs ($M=2$): `JD-BROAD-01`, `02`, `03`, `04`, `05`, `06`, `07`, `08`, `12`.
   - Triple-domain JDs ($M=3$): `JD-BROAD-09`.

---

## 4. Edge-Case Coverage Across Cohorts

Within each of the 12 JD cohorts ($N=20$), candidate profiles are stratified across standardized archetypes and deliberate edge cases:

| Candidate Index ($k$) | Candidate Archetype | Edge Case Marker | Tenure Ratio ($D$) | Expected Score Mechanics & Behavioral Safeguard | Human Grade |
| :---: | :--- | :--- | :---: | :--- | :---: |
| **#1** | **Lead Domain Expert** | `tenure_saturation` | $1.25 \to 1.000$ | Full tenure saturation ($D=1.000$), dual-domain match ($S_{\text{agg}} \ge 0.88$). | **Grade 3** |
| **#2** | **Veteran Architect** | `multi_role_excellence` | $1.10 \to 1.000$ | Multi-role history using max calibrated similarity per domain. | **Grade 3** |
| **#3** | **Principal Specialist** | `adjudicated_depth` | $1.00 \to 1.000$ | High domain depth, rater adjudication verified ($r_1=3, r_2=2 \implies 3$). | **Grade 3** |
| **#4** | **Single-Domain Specialist** | `unsupported_domain_zero_fill` | $1.00 \to 1.000$ | Preferred domain zero-filling: $S_1 = 0.86, S_2 = 0.00 \implies S_{\text{agg}} = 0.430$. | **Grade 2** |
| **#5** | **Senior Engineer (65% Damping)** | `proportional_damping_065` | $0.65 \to 0.650$ | Linear tenure damping: $D = 0.650, E = 100 \times S_{\text{agg}} \times 0.65$. | **Grade 2** |
| **#6** | **Mid-Level Engineer (50% Damping)** | `proportional_damping_050` | $0.50 \to 0.500$ | Linear tenure damping: $D = 0.500, E = 100 \times S_{\text{agg}} \times 0.50$. | **Grade 2** |
| **#7** | **Broad Generalist** | `moderate_similarity` | $1.00 \to 1.000$ | Saturated tenure, moderate similarity ($S_{\text{agg}} \approx 0.68$). | **Grade 2** |
| **#8** | **Junior Practitioner** | `adjacent_domain_low_tenure` | $0.25 \to 0.250$ | Low tenure damping ($D=0.250$), adjacent domain ($S_{\text{agg}} \approx 0.55$). | **Grade 1** |
| **#9** | **Experienced Misaligned Dev** | `peripheral_experience` | $1.00 \to 1.000$ | Saturated tenure, but irrelevant peripheral technology ($S_{\text{agg}} \le 0.30$). | **Grade 1** |
| **#10** | **Non-Technical Irrelevant** | `rule10_irrelevant` | $0.00 \to 0.000$ | Rule 10: Completely non-technical role (Retail/Service). Strict zeroing ($E=0.00$). | **Grade 0** |
| **#11** | **Early Career High Aptitude** | `exact_damping_025` | $0.25 \to 0.250$ | Exact 25% duration attainment stress-test ($D = 0.2500$). | **Grade 2** |
| **#12** | **Mid-Level Rising Dev** | `exact_damping_075` | $0.75 \to 0.750$ | Exact 75% duration attainment stress-test ($D = 0.7500$). | **Grade 2** |
| **#13** | **Distinguished Fellow** | `tenure_clamping_15y` | $2.50 \to 1.000$ | Long-tenure clamping stress-test: 15+ years tenure clamped to $D = 1.000$. | **Grade 3** |
| **#14** | **Concurrent Overlapping Roles** | `overlapping_concurrent` | $0.70 \to 0.700$ | Approved time-sliced pooling: concurrent roles evaluated using $\max(r_k)$. | **Grade 2** |
| **#15** | **Contractor Specialist** | `fragmented_tenure` | $1.00 \to 1.000$ | 4 non-overlapping short stints ($<8$ mo each) correctly summed without loss. | **Grade 2** |
| **#16** | **Unverified Dates Profile** | `missing_dates` | $0.00 \to 0.000$ | Missing employment dates safeguard: $D = 0.000, E = 0.00$, note `"missing_dates"`. | **Grade 2** |
| **#17** | **Inverted / Malformed Dates** | `invalid_date_range` | $0.00 \to 0.000$ | Start date > end date safeguard: $D = 0.000, E = 0.00$, note `"invalid_date_range"`. | **Grade 1** |
| **#18** | **Paradigm Safeguard Profile** | `unbounded_g1c` (Unbounded JDs) / `subthreshold_tenure_zero_duration` (Non-Unbounded JDs) | $0.00 \to 0.000$ | In Unbounded JDs (08, 12): Gate 1 Rule C duration zeroing ($D=0.000, E=0.00$, note `"unspecified"`), **Grade 3**. In Non-Unbounded JDs (10 JDs): Sub-threshold tenure zero duration ($D=0.000, E=0.00$, note `"duration_calculated"`), **Grade 1**. | **Grade 3** (Unbounded) / **Grade 1** (Non-Unbounded) |
| **#19** | **Stability Twin Alpha** | `twin_stability_pair` | $1.00 \to 1.000$ | Canonical profile for deterministic stability and tie-handling verification. | **Grade 3** |
| **#20** | **Stability Twin Beta** | `twin_stability_pair` | $1.00 \to 1.000$ | Identical duplicate to Twin Alpha; must produce exact identical score & rank. | **Grade 3** |

---

## 5. Ground-Truth Label Design & Model Output Separation

To prevent benchmark circularity, data snooping, and score leakage:

1. **Physical Separation of Dictionaries:**
   - Candidate input profiles are stored in `SYNTHETIC_BROAD_CANDIDATE_FIXTURES`.
   - Independent human ground truth is stored in `BROAD_GROUND_TRUTH_LABELS`.
   - `SYNTHETIC_BROAD_CANDIDATE_FIXTURES` contains zero expected model scores, zero component scores, and zero rank targets.
2. **Ground-Truth Label Schema:**
   ```python
   BROAD_GROUND_TRUTH_LABELS[candidate_id] = {
       "candidate_id": str,
       "target_jd": str,
       "grade": int,              # 4-level integer grade: 0, 1, 2, or 3
       "label": str,              # Human readable rubric string
       "r1": int,                 # Rater 1 grade
       "r2": int,                 # Rater 2 grade
       "adjudicated": bool,       # True if blind adjudication was required
       "binary_relevance": int,   # 1 if grade >= 2 else 0
   }
   ```
3. **Exhaustive Ground-Truth Denominator:**
   - Every candidate is labeled across all 12 cohorts.
   - Ground-truth distribution per 20-candidate cohort:
     - **In 10 Non-Unbounded Cohorts (`JD-BROAD-01` to `07`, `09` to `11`):**
       - Grade 3 (Exceptional Fit): **6 candidates** (#1, #2, #3, #13, #19, #20)
       - Grade 2 (Good / Partial Fit): **9 candidates** (#4, #5, #6, #7, #11, #12, #14, #15, #16)
       - Grade 1 (Marginal Fit): **4 candidates** (#8, #9, #17, #18)
       - Grade 0 (Unqualified / Irrelevant): **1 candidate** (#10)
       - **Relevant per cohort ($R_{\text{cohort}}$ where Grade $\ge 2$): Exactly 15 candidates**
       - **Non-Relevant per cohort: Exactly 5 candidates**
     - **In 2 Unbounded Cohorts (`JD-BROAD-08`, `12`):**
       - Grade 3 (Exceptional Fit): **7 candidates** (#1, #2, #3, #13, #18, #19, #20)
       - Grade 2 (Good / Partial Fit): **9 candidates** (#4, #5, #6, #7, #11, #12, #14, #15, #16)
       - Grade 1 (Marginal Fit): **3 candidates** (#8, #9, #17)
       - Grade 0 (Unqualified / Irrelevant): **1 candidate** (#10)
       - **Relevant per cohort ($R_{\text{cohort}}$ where Grade $\ge 2$): Exactly 16 candidates**
       - **Non-Relevant per cohort: Exactly 4 candidates**
   - **Total Broad Cohort Ground-Truth Aggregates (240 Candidates across 12 JDs):**
     - Grade 3: **74 candidates** ($(10 \times 6) + (2 \times 7)$)
     - Grade 2: **108 candidates** ($12 \times 9$)
     - Grade 1: **46 candidates** ($(10 \times 4) + (2 \times 3)$)
     - Grade 0: **12 candidates** ($12 \times 1$)
     - **Total Relevant Candidates ($R_{\text{total}}$ where Grade $\ge 2$): Exactly 182 candidates** ($150 + 32$)
     - **Total Non-Relevant Candidates: Exactly 58 candidates** ($50 + 8$)
   - This provides mathematically verified denominators for Recall@3 and Recall@5 calculation without estimation.

---

## 6. Reproducibility & Synthetic Data Hygiene

1. **Deterministic Generators:** All candidate IDs, names, company names, and date strings are generated through deterministic indexing without random number generators (`random` was not imported).
2. **Zero Personally Identifiable Information (PII):**
   - All candidate names are explicitly suffixed with `(Synthetic)` (e.g. `"Alex Mercer_1 (Synthetic)"`).
   - All company names are fictionalized with synthetic markers (e.g. `"Apex Systems (Synthetic)"`, `"Consulting Stint 1 (Synthetic)"`).
   - Zero telephone numbers, email addresses, or physical street addresses are included.
3. **Non-Invasive Accessor Interface:**
   - `get_broad_candidate_match_result(cid)`: Returns input matching payload ready for `RankingEngine.score_candidate()`.
   - `get_broad_candidate_ground_truth(cid)`: Returns independent human ground-truth label.
   - `get_broad_candidate_meta(cid)`: Returns archetype and edge markers.
   - `get_broad_jd_cohort_candidate_ids(jd_id)`: Returns the 20 candidate IDs for any JD.

---

## 7. Static Validation Results

1. **Bytecode Syntax Compilation:**
   ```powershell
   python -m py_compile tests/pilot/fixtures_broad.py
   ```
   - **Exit Code:** `0`
   - **Result:** Clean compilation, 0 syntax errors, 0 warnings.
2. **Lightweight Structural Integrity Verification:**
   Executed `verify_broad_fixtures_integrity()` in isolation:
   - `job_descriptions_count`: **12**
   - `candidates_count`: **240**
   - `ground_truth_labels_count`: **240**
   - `errors`: `[]` (Zero structural errors)
   - **Integrity Status:** **PASS**

---

## 8. Safety Invariants & Scope Verification

| Safety Invariant | Verification Method & Finding | Status |
| :--- | :--- | :---: |
| **No Test Execution** | Pilot test suite was NOT executed during Stage 5E.3.2. | **CONFIRMED** |
| **No Metric Calculations** | Zero ranking scores or IR metrics were calculated. | **CONFIRMED** |
| **Existing Pilot Fixtures Untouched** | [fixtures.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/fixtures.py) timestamp untouched since 15:06. | **CONFIRMED** |
| **Existing Pilot Metrics Untouched** | [metrics.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/metrics.py) timestamp untouched since 15:06. | **CONFIRMED** |
| **Existing Pilot Tests Untouched** | [test_stage_5e2_pilot.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/test_stage_5e2_pilot.py) untouched since 15:52. | **CONFIRMED** |
| **Production Code Untouched** | Ranking engine, schemas, weights, formulas, thresholds, and `.env` untouched. | **CONFIRMED** |
| **Feature Flag Immutability** | `USE_EVIDENCE_BASED_EXPERIENCE` remains strictly `False`. | **CONFIRMED** |
| **MongoDB & Production Isolation** | Zero database connections; batch `07281a64-46cf-46b4-a5c1-a0d46b13e7b2` untouched. | **CONFIRMED** |
| **Resume Storage Untouched** | No resumes uploaded, extracted, or processed. | **CONFIRMED** |
| **No Progression to Stage 5E.3.3** | Work halted immediately following Stage 5E.3.2 report generation. | **CONFIRMED** |

---

## 9. Stopping Point & Recommendations

Stage 5E.3.2 is complete. In strict adherence to your instructions:
- Antigravity has stopped and will not execute any ranking runs or metric evaluations.
- The broad synthetic dataset is fully constructed, statically compiled, and verified.
- We await user review and explicit authorization before proceeding to **Stage 5E.3.3: Execution of Broad Synthetic Suite & IR Benchmarking**.
