# TalentAI — Stage 5E.2.3.1: Isolated Pilot Harness Repair Report

**Date:** 2026-10-31  
**Stage:** 5E.2.3.1 (Isolated Pilot Harness Repair ONLY)  
**Execution Authority:** Explicit Authorization for Harness Repair Only (No Pilot Execution, No Metric Computation)  
**Safety Invariant:** Read-only inspection of production schemas; test harness repairs strictly confined to `tests/pilot/test_stage_5e2_pilot.py`.

---

## 1. Executive Summary

During Stage 5E.2.3 execution, the pilot test runner `tests/pilot/test_stage_5e2_pilot.py` executed 26 deterministic tests. 11 tests passed cleanly, and 15 tests produced `AttributeError` errors. As identified in the Stage 5E.2.3 execution report, all 15 errors were caused by schema accessor mismatches between test assertions and the production `CandidateRankingResult` and `CategoryScoreBreakdown` Pydantic schemas.

In this narrow repair stage (Stage 5E.2.3.1):
1. **Schema Definitions Confirmed from Source:** The production schemas in [backend/app/ranking/ranking_schemas.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_schemas.py) and [backend/app/ranking/ranking_service.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_service.py) were thoroughly inspected to establish exact field names and types.
2. **Harness Repaired:** All 15 mismatched schema accessors in [tests/pilot/test_stage_5e2_pilot.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/test_stage_5e2_pilot.py) were updated to accurately reference production fields.
3. **Strict Invariants Upheld:**
   - Zero test execution occurred (`unittest` was not executed).
   - Zero metric calculation occurred.
   - Expected mathematical values, scoring formulas, fixtures, and test intents were preserved 100% without alteration.
   - Zero production code, configuration, or environment files were modified.
   - Feature flag `USE_EVIDENCE_BASED_EXPERIENCE` remains strictly `False`.

---

## 2. Production Schema Fields Confirmed from Source

Direct inspection of [backend/app/ranking/ranking_schemas.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_schemas.py) and [backend/app/ranking/ranking_service.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_service.py) confirmed the following exact schema structures:

### 2.1 `CandidateRankingResult` Schema ([ranking_schemas.py:L145-L188](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_schemas.py#L145-L188))

| Schema Field | Type | Description | Test Discrepancy Found in Stage 5E.2.3 |
| :--- | :--- | :--- | :--- |
| `final_score` | `float \| None` | Overall weighted candidate score (0.0 to 100.0). | Test incorrectly accessed `.score` instead of `.final_score`. |
| `breakdown` | `dict[str, CategoryScoreBreakdown]` | Detailed explainable breakdown mapping category names to score objects. | Test incorrectly accessed `.category_breakdown` instead of `.breakdown`. |
| `component_scores` | `dict[str, float \| None]` | Quick mapping of component name to numeric score. | Not used by harness assertions. |
| `experience_diagnostic` | `MinimumExperienceDiagnostic` | Separate duration diagnostic data. | Not accessed via breakdown dictionary. |
| `warnings` | `list[str]` | Informational diagnostics. | Not used by harness assertions. |
| `errors` | `list[str]` | Technical service failure strings. | Not used by harness assertions. |

### 2.2 `CategoryScoreBreakdown` Schema ([ranking_schemas.py:L70-L117](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_schemas.py#L70-L117))

| Schema Field | Type | Description | Test Discrepancy Found in Stage 5E.2.3 |
| :--- | :--- | :--- | :--- |
| `category` | `str` | Name of the scoring category. | Valid. |
| `status` | `CategoryApplicability` | Evaluation status (`"complete"`, `"not_applicable"`, etc.). | Valid. |
| `score` | `float \| None` | Calculated category score (0.0 to 100.0). | Valid on `CategoryScoreBreakdown`, but was accessed via wrong dictionary name. |
| `original_weight` | `float` | Base weight before dynamic renormalization. | Valid. |
| `normalized_weight` | `float` | Dynamically renormalized weight applied during evaluation. | Test incorrectly accessed `.weight` instead of `.normalized_weight`. |
| `weighted_contribution` | `float \| None` | Score multiplied by normalized weight (`normalized_weight * score`). | Valid. |
| `evidence` | `list[dict[str, Any]]` | Transparent evidence summaries or provenance references. | Valid on `CategoryScoreBreakdown`, but was accessed via wrong dictionary name. |
| `notes` | `str \| None` | Diagnostic commentary string. | Valid on `CategoryScoreBreakdown`, but was accessed via wrong dictionary name. |

### 2.3 Category Dictionary Keys in `breakdown` ([ranking_service.py:L1396-L1480](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/backend/app/ranking/ranking_service.py#L1396-L1480))

The keys in `CandidateRankingResult.breakdown` are populated directly from `BASE_WEIGHTS`:
1. `"required_skills"` (Component A, base weight 0.25)
2. `"responsibilities"` (Component B, base weight 0.30)
3. `"tools_and_technologies"` (Component C, base weight 0.10)
4. `"experience_relevance"` (Component D, base weight 0.35)

**Root cause confirmed:** Test assertions in `test_stage_5e2_pilot.py` used `"experience"` instead of `"experience_relevance"`.

---

## 3. Files Changed and Repair Rationale

Only one file was modified: [tests/pilot/test_stage_5e2_pilot.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/test_stage_5e2_pilot.py).

### 3.1 Repair Details

| Line Range | Test Method | Original Code | Repaired Code | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| L100–L131 | `test_group_a_identical_inputs_and_components_a_b_c_invariance` | `res.category_breakdown[cat].score`<br>`res.category_breakdown[cat].weight` | `res.breakdown[cat].score`<br>`res.breakdown[cat].normalized_weight` | Align with `CandidateRankingResult.breakdown` dictionary and `CategoryScoreBreakdown.normalized_weight` field. |
| L146–L149 | `test_group_a_score_delta_attributable_only_to_component_d` | `score_leg = res_legacy.score`<br>`score_ev = res_evidence.score`<br>`exp_leg = res_legacy.category_breakdown["experience"].score`<br>`exp_ev = res_evidence.category_breakdown["experience"].score` | `score_leg = res_legacy.final_score`<br>`score_ev = res_evidence.final_score`<br>`exp_leg = res_legacy.breakdown["experience_relevance"].score`<br>`exp_ev = res_evidence.breakdown["experience_relevance"].score` | Align with `res.final_score`, `res.breakdown`, and key `"experience_relevance"`. |
| L196 | `test_group_b_bounded_range_duration_saturation` | `exp_breakdown = res_ev.category_breakdown["experience"]` | `exp_breakdown = res_ev.breakdown["experience_relevance"]` | Align with `res.breakdown["experience_relevance"]`. |
| L212–L213 | `test_group_b_proportional_duration_damping` | `res_02.category_breakdown["experience"].score`<br>`res_10.category_breakdown["experience"].score` | `res_02.breakdown["experience_relevance"].score`<br>`res_10.breakdown["experience_relevance"].score` | Align with `res.breakdown["experience_relevance"]`. |
| L223 | `test_group_b_irrelevant_experience_zero_score` | `res.category_breakdown["experience"].score` | `res.breakdown["experience_relevance"].score` | Align with `res.breakdown["experience_relevance"]`. |
| L235 | `test_group_b_missing_date_safeguard` | `exp_breakdown = res_ev.category_breakdown["experience"]` | `exp_breakdown = res_ev.breakdown["experience_relevance"]` | Align with `res.breakdown["experience_relevance"]`. |
| L247 | `test_group_b_g1c_unbounded_experience_safeguard` | `exp_breakdown = res_ev.category_breakdown["experience"]` | `exp_breakdown = res_ev.breakdown["experience_relevance"]` | Align with `res.breakdown["experience_relevance"]`. |
| L259 | `test_group_b_multiple_roles_maximum_semantic_similarity` | `exp_breakdown = res_ev.category_breakdown["experience"]` | `exp_breakdown = res_ev.breakdown["experience_relevance"]` | Align with `res.breakdown["experience_relevance"]`. |
| L275 | `test_group_b_unsupported_jd_domain_zero_filling` | `exp_breakdown = res_ev.category_breakdown["experience"]` | `exp_breakdown = res_ev.breakdown["experience_relevance"]` | Align with `res.breakdown["experience_relevance"]`. |
| L341 | `test_group_b_case_insensitive_domain_deduplication` | `exp_breakdown = res.category_breakdown["experience"]` | `exp_breakdown = res.breakdown["experience_relevance"]` | Align with `res.breakdown["experience_relevance"]`. |
| L501 | `test_group_e_evidence_source_traceability` | `evidence = res.category_breakdown["experience"].evidence` | `evidence = res.breakdown["experience_relevance"].evidence` | Align with `res.breakdown["experience_relevance"]`. |
| L518 | `test_group_e_missing_date_diagnostics` | `notes = res.category_breakdown["experience"].notes` | `notes = res.breakdown["experience_relevance"].notes` | Align with `res.breakdown["experience_relevance"]`. |
| L528 | `test_group_e_g1c_diagnostic_status_and_alerts` | `notes = res.category_breakdown["experience"].notes` | `notes = res.breakdown["experience_relevance"].notes` | Align with `res.breakdown["experience_relevance"]`. |
| L541–L542 | `test_group_e_zero_score_vs_missing_information_distinction` | `note_08 = str(res_08.category_breakdown["experience"].notes)`<br>`note_06 = str(res_06.category_breakdown["experience"].notes)` | `note_08 = str(res_08.breakdown["experience_relevance"].notes)`<br>`note_06 = str(res_06.breakdown["experience_relevance"].notes)` | Align with `res.breakdown["experience_relevance"]`. |
| L555 | `test_group_e_g1c_domain_evidence_preservation_despite_zero_duration` | `evidence = res.category_breakdown["experience"].evidence` | `evidence = res.breakdown["experience_relevance"].evidence` | Align with `res.breakdown["experience_relevance"]`. |

---

## 4. Preservation of Expected Values and Test Intent

In strict adherence to the Stage 5E.2.3.1 constraints:
- **No Expected Values Were Changed:** All numeric assertion targets remain identical:
  - Saturation score: `87.00`
  - Damped scores: `40.50` and `31.50`
  - Zero scores: `0.00`
  - Multi-role max similarity: `82.50`
  - Unsupported domain zero-filling: `43.00`
  - Case-insensitive deduplication: `80.00`
  - Formula weight multiplier: `0.35`
  - Calibrated similarity provenance: `0.88`
- **No Fixtures Were Changed:** [tests/pilot/fixtures.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/fixtures.py) remains completely untouched.
- **No Metric Calculations Were Changed:** [tests/pilot/metrics.py](file:///c:/Users/siddh/OneDrive/Desktop/Talent_AI/tests/pilot/metrics.py) remains completely untouched.
- **Test Intent Preserved:** The assertions test the exact same physical and mathematical behaviors approved in Stage 5E.2.1. Only the schema field accessor syntax was corrected.

---

## 5. Complete Unified Diff Summary

```diff
--- a/tests/pilot/test_stage_5e2_pilot.py
+++ b/tests/pilot/test_stage_5e2_pilot.py
@@ -99,32 +99,32 @@ class TestStage5E2PilotRunner(unittest.TestCase):
         # Component A: Required Skills (25%)
         self.assertEqual(
-            res_legacy.category_breakdown["required_skills"].score,
-            res_evidence.category_breakdown["required_skills"].score,
+            res_legacy.breakdown["required_skills"].score,
+            res_evidence.breakdown["required_skills"].score,
             "Component A score must be strictly identical between engines.",
         )
         self.assertEqual(
-            res_legacy.category_breakdown["required_skills"].weight,
-            res_evidence.category_breakdown["required_skills"].weight,
+            res_legacy.breakdown["required_skills"].normalized_weight,
+            res_evidence.breakdown["required_skills"].normalized_weight,
             "Component A weight must be strictly identical between engines.",
         )
 
         # Component B: Responsibilities (30%)
         self.assertEqual(
-            res_legacy.category_breakdown["responsibilities"].score,
-            res_evidence.category_breakdown["responsibilities"].score,
+            res_legacy.breakdown["responsibilities"].score,
+            res_evidence.breakdown["responsibilities"].score,
             "Component B score must be strictly identical between engines.",
         )
         self.assertEqual(
-            res_legacy.category_breakdown["responsibilities"].weight,
-            res_evidence.category_breakdown["responsibilities"].weight,
+            res_legacy.breakdown["responsibilities"].normalized_weight,
+            res_evidence.breakdown["responsibilities"].normalized_weight,
             "Component B weight must be strictly identical between engines.",
         )
 
         # Component C: Tools & Technologies (10%)
         self.assertEqual(
-            res_legacy.category_breakdown["tools_and_technologies"].score,
-            res_evidence.category_breakdown["tools_and_technologies"].score,
+            res_legacy.breakdown["tools_and_technologies"].score,
+            res_evidence.breakdown["tools_and_technologies"].score,
             "Component C score must be strictly identical between engines.",
         )
         self.assertEqual(
-            res_legacy.category_breakdown["tools_and_technologies"].weight,
-            res_evidence.category_breakdown["tools_and_technologies"].weight,
+            res_legacy.breakdown["tools_and_technologies"].normalized_weight,
+            res_evidence.breakdown["tools_and_technologies"].normalized_weight,
             "Component C weight must be strictly identical between engines.",
         )
@@ -145,10 +145,10 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        score_leg = res_legacy.score
-        score_ev = res_evidence.score
-        exp_leg = res_legacy.category_breakdown["experience"].score
-        exp_ev = res_evidence.category_breakdown["experience"].score
+        score_leg = res_legacy.final_score
+        score_ev = res_evidence.final_score
+        exp_leg = res_legacy.breakdown["experience_relevance"].score
+        exp_ev = res_evidence.breakdown["experience_relevance"].score
@@ -195,3 +195,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        exp_breakdown = res_ev.category_breakdown["experience"]
+        exp_breakdown = res_ev.breakdown["experience_relevance"]
@@ -211,4 +211,4 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        self.assertEqual(res_02.category_breakdown["experience"].score, 40.50)
-        self.assertEqual(res_10.category_breakdown["experience"].score, 31.50)
+        self.assertEqual(res_02.breakdown["experience_relevance"].score, 40.50)
+        self.assertEqual(res_10.breakdown["experience_relevance"].score, 31.50)
@@ -222,3 +222,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
             self.assertEqual(
-                res.category_breakdown["experience"].score,
+                res.breakdown["experience_relevance"].score,
                 0.00,
@@ -234,3 +234,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        exp_breakdown = res_ev.category_breakdown["experience"]
+        exp_breakdown = res_ev.breakdown["experience_relevance"]
@@ -246,3 +246,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        exp_breakdown = res_ev.category_breakdown["experience"]
+        exp_breakdown = res_ev.breakdown["experience_relevance"]
@@ -258,3 +258,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        exp_breakdown = res_ev.category_breakdown["experience"]
+        exp_breakdown = res_ev.breakdown["experience_relevance"]
@@ -274,3 +274,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        exp_breakdown = res_ev.category_breakdown["experience"]
+        exp_breakdown = res_ev.breakdown["experience_relevance"]
@@ -340,3 +340,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
         res = self.engine_evidence.score_candidate(match_result, jd_dup)
-        exp_breakdown = res.category_breakdown["experience"]
+        exp_breakdown = res.breakdown["experience_relevance"]
@@ -500,3 +500,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
         res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_01)
-        evidence = res.category_breakdown["experience"].evidence
+        evidence = res.breakdown["experience_relevance"].evidence
@@ -517,3 +517,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
         res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_01)
-        notes = res.category_breakdown["experience"].notes
+        notes = res.breakdown["experience_relevance"].notes
@@ -527,3 +527,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
         res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_03)
-        notes = res.category_breakdown["experience"].notes
+        notes = res.breakdown["experience_relevance"].notes
@@ -540,4 +540,4 @@ class TestStage5E2PilotRunner(unittest.TestCase):
-        note_08 = str(res_08.category_breakdown["experience"].notes)
-        note_06 = str(res_06.category_breakdown["experience"].notes)
+        note_08 = str(res_08.breakdown["experience_relevance"].notes)
+        note_06 = str(res_06.breakdown["experience_relevance"].notes)
@@ -554,3 +554,3 @@ class TestStage5E2PilotRunner(unittest.TestCase):
         res = self.engine_evidence.score_candidate(get_candidate_match_result(cand_id), JD_PILOT_03)
-        evidence = res.category_breakdown["experience"].evidence
+        evidence = res.breakdown["experience_relevance"].evidence
```

---

## 6. Static Syntax Validation Results

The modified test runner file was statically validated via Python's bytecode compiler:

- **Command:**
  ```powershell
  python -m py_compile tests/pilot/test_stage_5e2_pilot.py
  ```
- **Exit Code:** `0`
- **Output:** Clean compilation, 0 syntax errors, 0 warnings.

---

## 7. Safety Invariants & Scope Verification

| Safety Invariant | Verification Method | Status |
| :--- | :--- | :---: |
| **No Pilot Test Execution** | `unittest.main()` or runner execution was NOT invoked during Stage 5E.2.3.1. | **CONFIRMED** |
| **No Metric Calculations** | No ranking scores or IR metrics were calculated in this stage. | **CONFIRMED** |
| **Changes Limited to `tests/pilot/`** | File timestamp inspection confirmed only `test_stage_5e2_pilot.py` was modified. | **CONFIRMED** |
| **Production Code Unmodified** | `backend/app/ranking/ranking_schemas.py`, `ranking_service.py`, and `ranking_config.py` timestamps are untouched since Oct 28–30. | **CONFIRMED** |
| **Configuration & `.env` Unmodified** | `backend/.env` is untouched since Oct 28. | **CONFIRMED** |
| **Feature Flag Remains `False`** | Inspection of `ranking_config.py:L82-L85` confirms `USE_EVIDENCE_BASED_EXPERIENCE` defaults to `False`. | **CONFIRMED** |
| **MongoDB & Database Untouched** | Zero MongoDB connections or queries; database `talent_ai` remains untouched. | **CONFIRMED** |
| **Active Batches & Resumes Untouched** | Active batch `07281a64-46cf-46b4-a5c1-a0d46b13e7b2` and `backend/data/` folders remain untouched. | **CONFIRMED** |
| **No Live APIs Called** | Zero network or HTTP requests executed. | **CONFIRMED** |
| **No Progression to Stage 5E.3** | Work is halted immediately following Stage 5E.2.3.1 harness repair. | **CONFIRMED** |

---

## 8. Blockers & Unresolved Issues

- **Blockers:** None. All 15 schema mismatches were localized test-harness accessor discrepancies and did not require any modifications to production code, schemas, or algorithms.
- **Unresolved Issues:** None.

---

## 9. Next Steps

Stage 5E.2.3.1 is complete. We await user authorization to proceed with **Stage 5E.2.3.2: Re-execution of Isolated Synthetic Pilot Test Runner**.
