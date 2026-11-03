# TalentAI — Production Scoring Migration Report: Legacy to Evidence-Based Experience Scoring

**Project:** TalentAI — AI Resume Shortlister  
**Document:** Production Scoring Migration Report (`project_closeout/PRODUCTION_SCORING_MIGRATION_REPORT.md`)  
**Date:** 31 October 2026  
**Migration Target:** Original Production Ranking Pipeline (`/ranking/...`)  
**Default Engine:** **Evidence-Based Experience Scoring** ($E = 100 \times S_{\text{agg}} \times D$)  
**Rollback Engine:** Legacy Categorical Scoring ($E \in \{0, 40, 70, 100\}$)  
**Production Feature Flag:** `USE_EVIDENCE_BASED_EXPERIENCE = True`  
**Rollout Boundary:** Code-level production migration verified using synthetic test fixtures only. Real-data processing remains strictly BLOCKED pending formal external authorization.

---

## 1. Executive Summary

TalentAI’s original production resume-ranking pipeline has been migrated from the Legacy Categorical Experience Scoring engine to the continuous **Evidence-Based Experience Scoring engine**.

Evidence-Based scoring is now the configured production default across all production ranking endpoints:
- Single-resume evaluation (`POST /ranking/rank-resume`)
- Synchronous batch ranking (`POST /ranking/rank-batch`)
- Asynchronous batch ranking background orchestration (`POST /ranking/rank-batch-async` -> worker -> `GET /ranking/jobs/{job_id}`)

The Legacy categorical engine has been preserved in its entirety as a zero-risk rollback option, accessible via environment configuration (`USE_EVIDENCE_BASED_EXPERIENCE=false`) or per-request override (`"use_evidence_based_experience": false`).

All 11 migration test assertions passed under isolated synthetic testing. Zero real resumes, production database collections, the protected active batch (`07281a64-46cf-46b4-a5c1-a0d46b13e7b2`), and the backup directory were touched.

---

## 2. Original Production Ranking Path & Architecture

### 2.1 Production Request-to-Scoring Pipeline
The original production ranking path was identified and traced from HTTP ingress to database storage:

```
[Ingress API Router]
  backend/app/api/ranking.py
    ├── POST /ranking/rank-resume         -> ranking_engine.rank_resume()
    ├── POST /ranking/rank-batch          -> ranking_engine.rank_batch()
    └── POST /ranking/rank-batch-async    -> ranking_engine.create_and_start_ranking_job()
                                                └── asyncio.create_task(execute_ranking_job())
[Ranking Service Core]
  backend/app/ranking/ranking_service.py
    └── RankingEngine.score_candidate()
          ├── Component A: calculate_required_skills_score()         (Weight: 25%)
          ├── Component B: calculate_responsibilities_score()       (Weight: 30%)
          ├── Component C: calculate_tools_score()                  (Weight: 10%)
          └── Component D: Experience Relevance                      (Weight: 35%)
                │
                ├── [Default: USE_EVIDENCE_BASED_EXPERIENCE = True]
                │     └── calculate_evidence_based_experience_score()
                │           Formula: E = 100 * S_agg * D_global
                │           Notes: "Scoring method: evidence_based"
                │
                └── [Rollback: USE_EVIDENCE_BASED_EXPERIENCE = False]
                      └── calculate_experience_relevance_score()
                            Formula: E in {0, 40, 70, 100}
                            Notes: Categorical mapping
```

### 2.2 Mathematical Formulation & Invariance
The 4-component weighted scoring architecture is strictly preserved:
$$\text{Final Score} = 0.25 A + 0.30 B + 0.10 C + 0.35 D$$

- **Component A (Required Skills):** 25% base weight.
- **Component B (Responsibilities):** 30% base weight.
- **Component C (Tools & Technologies):** 10% base weight.
- **Component D (Experience Relevance):** 35% base weight. Now computed continuously via Evidence-Based scoring:
  $$E = 100 \times S_{\text{agg}} \times D_{\text{global}}$$
  where:
  - $S_{\text{agg}} = \frac{1}{M}\sum_{m=1}^{M} S_m$ (mean calibrated cosine similarity across preferred JD domains).
  - $D_{\text{global}} = \min(1.0, Y_{\text{cand}} / Y_{\text{target}})$ (non-overlapping relevant duration saturated against JD target tenure).

---

## 3. Files Changed and Technical Rationale

| File | Changes Made | Rationale |
|---|---|---|
| [`backend/app/ranking/ranking_config.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_config.py) | Changed `default=False` to `default=True` in `USE_EVIDENCE_BASED_EXPERIENCE = parse_bool_env(...)` | Configures Evidence-Based experience scoring as the production default while preserving environment-based boolean override. |
| [`backend/app/ranking/ranking_schemas.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_schemas.py) | Added optional `use_evidence_based_experience: bool \| None = None` to `RankResumeRequest` and `RankBatchRequest` | Allows API clients to specify an engine override per-request for rollback or testing, defaulting to `None` (which defers to production flag). |
| [`backend/app/ranking/ranking_service.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_service.py) | Updated `rank_resume()`, `rank_batch()`, `create_and_start_ranking_job()`, and `execute_ranking_job()` to accept and propagate `use_evidence_based_experience` to `score_candidate()` | Ensures the production ranking path forwards engine selection through synchronous and background execution flows. |
| [`backend/app/api/ranking.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/api/ranking.py) | Passed `use_evidence_based_experience=request.use_evidence_based_experience` in routes `/rank-resume`, `/rank-batch`, and `/rank-batch-async` | Connects HTTP request body parameter directly to `ranking_engine`. |
| [`frontend/src/api/rankingApi.js`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/frontend/src/api/rankingApi.js) | Added optional `use_evidence_based_experience` parameter to `startAsyncRanking()`, `rankResume()`, and `rankBatchSync()` | Enables frontend client to request specific scoring engines when needed. |
| [`backend/test_demo_api.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/test_demo_api.py) | Updated Test 8 assertion to verify `USE_EVIDENCE_BASED_EXPERIENCE is True` | Aligns demo suite feature flag check to new production default. |
| [`backend/test_ranking_stage_5c.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/test_ranking_stage_5c.py) | Updated Test 1 to verify `USE_EVIDENCE_BASED_EXPERIENCE is True` while verifying `RankingEngine(use_evidence_based_experience=False)` performs legacy scoring | Verifies both production default and rollback behavior. |
| [`backend/test_stage_5b1_hardening.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/test_stage_5b1_hardening.py) | Updated regression assertion to verify `USE_EVIDENCE_BASED_EXPERIENCE is True` | Aligns Stage 5B.1 regression test suite to new production default. |
| [`backend/test_production_scoring_migration.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/test_production_scoring_migration.py) | Created 11-case end-to-end synthetic migration and rollback validation suite | Comprehensive test suite covering default engine, formula execution, rollback, edge cases, invariants, and isolation. |

---

## 4. Exact Integration Points

1. **Singleton Default (`backend/app/ranking/ranking_service.py:2028`):**
   ```python
   ranking_engine = RankingEngine()
   ```
   Because `RankingEngine.__init__` reads `use_evidence_based_experience if use_evidence_based_experience is not None else USE_EVIDENCE_BASED_EXPERIENCE`, and `USE_EVIDENCE_BASED_EXPERIENCE` now defaults to `True`, the global `ranking_engine` singleton initializes with `self.use_evidence_based_experience = True`.

2. **Core Scoring Dispatch (`backend/app/ranking/ranking_service.py:1372-1393`):**
   ```python
   active_use_evidence = (
       use_evidence_based_experience
       if use_evidence_based_experience is not None
       else self.use_evidence_based_experience
   )

   if active_use_evidence:
       score_exp, status_exp, total_exp, qual_exp, evid_exp, note_exp = (
           self.calculate_evidence_based_experience_score(
               experience_matching_data=exp_data,
               job_description=job_description,
               relevance_decisions=relevance_decisions,
           )
       )
   else:
       score_exp, status_exp, total_exp, qual_exp, evid_exp, note_exp = (
           self.calculate_experience_relevance_score(
               experience_matching_data=exp_data,
               job_description=job_description,
               relevance_decisions=relevance_decisions,
           )
       )
   ```

3. **Frontend Provenance Detection (`frontend/src/components/ranking/ExperienceExplainabilitySection.jsx:76`):**
   ```javascript
   const isEvidenceBased = notes.includes('Scoring method: evidence_based');
   ```
   When `isEvidenceBased` is true, the UI automatically displays:
   - "Evidence-Based Experience Scoring" badge
   - Dual metrics ($S_{\text{agg}}$ calibrated similarity + $D_{\text{global}}$ duration factor)
   - Per-domain calibrated semantic similarity breakdown
   - Duration saturation diagnostics and target tenure

---

## 5. Rollback Procedures

If an operational issue occurs, three distinct rollback levels are available:

### Level 1: Environment-Driven Global Rollback (Recommended)
Set the environment variable in `backend/.env` or the server execution environment:
```env
USE_EVIDENCE_BASED_EXPERIENCE=false
```
Restart the backend service. All ranking requests will immediately revert to Legacy Categorical Scoring without requiring code changes.

### Level 2: Request-Level Granular Rollback
Any production ranking request can selectively execute the Legacy engine by supplying `"use_evidence_based_experience": false` in the request body:
```json
POST /ranking/rank-resume
{
  "upload_id": "<batch_id>",
  "filename": "candidate.pdf",
  "use_evidence_based_experience": false
}
```
Or for batch ranking:
```json
POST /ranking/rank-batch-async
{
  "upload_id": "<batch_id>",
  "use_evidence_based_experience": false
}
```

### Level 3: Code-Level Rollback
In [`backend/app/ranking/ranking_config.py`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_config.py#L82), change:
```python
USE_EVIDENCE_BASED_EXPERIENCE: Final[bool] = parse_bool_env(
    "USE_EVIDENCE_BASED_EXPERIENCE",
    default=False,
)
```

### Verification of Selected Engine
Inspect the returned candidate breakdown:
- **Evidence-Based Engine:** `breakdown.experience_relevance.notes` contains `"Scoring method: evidence_based"`.
- **Legacy Engine:** `breakdown.experience_relevance.notes` is `None` or describes categorical scoring, and `breakdown.experience_relevance.score` is strictly one of $\{0.0, 40.0, 70.0, 100.0\}$.

---

## 6. Synthetic Test Execution Results

All tests executed successfully using synthetic fixtures and isolated test harnesses:

### 6.1 Dedicated Migration Suite (`backend/test_production_scoring_migration.py`)
Command: `python test_production_scoring_migration.py`
```
================================================================================
TALENTAI — PRODUCTION SCORING MIGRATION TEST SUITE
MIGRATION: LEGACY CATEGORICAL -> EVIDENCE-BASED EXPERIENCE SCORING
================================================================================
[PASSED] Test 1: Production configuration defaults to USE_EVIDENCE_BASED_EXPERIENCE = True with robust parsing
[PASSED] Test 2: Production RankingEngine instance defaults to Evidence-Based scoring
[PASSED] Test 3: Production scoring calculates E = 100 * S_agg * D and weighted final score accurately
[PASSED] Test 4: Legacy rollback engine restores categorical scoring (E=100.0, weight=35.0)
[PASSED] Test 5: Request-level override allows seamless per-request engine selection and rollback
[PASSED] Test 6: Candidate differentiation breaks Legacy categorical ties (90.0 vs 35.0)
[PASSED] Test 7: Components A, B, and C scores demonstrate exact mathematical invariance
[PASSED] Test 8: Diagnostic safeguards verified (missing_dates, invalid_date_range, unspecified, max_only)
[PASSED] Test 9: Request and response schemas serialize and deserialize cleanly
[PASSED] Test 10: Production ranking API executes Evidence-Based default and supports request rollback
[PASSED] Test 11: Safety boundary respected — zero access to MongoDB resumes, protected batch, or backup
================================================================================
ALL 11 PRODUCTION SCORING MIGRATION TESTS PASSED SUCCESSFULLY!
================================================================================
```

### 6.2 Existing Backend Suites Verified
- `python test_ranking_stage_5c.py`: **13 / 13 passed**
- `python test_stage_5b1_hardening.py`: **4 / 4 passed**
- `python test_demo_api.py`: **8 / 8 passed**
- `python test_ranking_api.py`: **7 / 7 passed (Cases 24–30)**

### 6.3 Frontend Vitest Suite
Command: `npx vitest run` in `frontend/`
```
 Test Files  5 passed (5)
      Tests  43 passed (43)
```

---

## 7. Governance, Safety & Rollout Boundary

> [!IMPORTANT]
> **Strict Operational Boundary Notice:**  
> The production ranking code path is now configured for Evidence-Based experience scoring. However, **real-data processing and live batch migration remain strictly BLOCKED**.

- **Stage 5E.4.0 Readiness Gate:** Remains **BLOCKED — PREREQUISITES PENDING**.
- **Governance Prerequisites:** All 10 approval prerequisites in [`project_closeout/APPROVAL_TRACKER.md`](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/project_closeout/APPROVAL_TRACKER.md) remain pending formal sign-off.
- **Safety Confirmation:**
  - Real resume records were **NEVER** read, uploaded, parsed, ranked, or exposed.
  - Active recruitment batch `07281a64-46cf-46b4-a5c1-a0d46b13e7b2` was **NOT** accessed or modified.
  - Backup directory `backup_pre_reset_20261028` was **NOT** touched or modified.
  - No database collections were dropped, cleaned, or reset.
