# TalentAI — Safe Synthetic Demonstration Guide

**Project:** TalentAI — AI Resume Shortlister  
**Document:** Safe Demo Guide (`project_closeout/SAFE_DEMO_GUIDE.md`)  
**Date:** 2026-10-31  
**Scope:** 100% Synthetic In-Memory Demonstration ONLY  
**Safety Invariant:** Zero access to real candidate resumes or personal data. Feature flag `USE_EVIDENCE_BASED_EXPERIENCE=False` strictly preserved in production.

---

## 1. Opening Disclaimer (Must Be Read Before Any Demonstration)

> [!IMPORTANT]
> **Mandatory Demonstration Disclaimer**  
> "This demonstration of TalentAI utilizes **100% synthetic in-memory test profiles and fictional Job Descriptions**.  
> - No real candidate resumes, personal data, or confidential employment histories are accessed or processed.  
> - Production database `talent_ai`, collection `resumes`, and active batch `07281a64-46cf-46b4-a5c1-a0d46b13e7b2` remain completely isolated and untouched.  
> - The production feature flag `USE_EVIDENCE_BASED_EXPERIENCE` is strictly set to `False`. Evidence-based scoring is demonstrated exclusively via in-memory, isolated test instances.  
> - TalentAI is an algorithmic decision-support tool designed for semantic shortlisting assistance; it is not an automated hiring decision-maker."

---

## 2. Pre-Flight Verification Checklist

Before initiating any demonstration, run the following verification checks in PowerShell:

### Check 1: Verify Working Directory
Ensure you are in the `backend/` directory so that pydantic settings resolve local `.env` correctly:
```powershell
cd C:\Users\siddh\OneDrive\Desktop\Talent_AI\backend
pwd
```

### Check 2: Verify Production Feature Flag is `False`
Confirm via Python that the global production feature flag defaults to `False`:
```powershell
python -c "from app.ranking.ranking_config import USE_EVIDENCE_BASED_EXPERIENCE; print('USE_EVIDENCE_BASED_EXPERIENCE:', USE_EVIDENCE_BASED_EXPERIENCE); assert USE_EVIDENCE_BASED_EXPERIENCE is False"
```
*Expected Output:*
```
USE_EVIDENCE_BASED_EXPERIENCE: False
```

### Check 3: Verify Synthetic Fixtures Integrity
Confirm that synthetic fixtures in `tests/pilot/fixtures_broad.py` pass all structural integrity checks:
```powershell
python -c "import sys; sys.path.insert(0, '../tests/pilot'); from fixtures_broad import verify_broad_fixtures_integrity; verify_broad_fixtures_integrity()"
```
*Expected Output:*
```
Broad fixtures integrity verification: PASSED (0 errors).
```

---

## 3. Step-by-Step Safe Demonstration Sequence

```mermaid
graph LR
    A["Pre-Flight Checks"] --> B["Step 1: Run Test Suite (26 Tests)"]
    B --> C["Step 2: 4-Component Architecture"]
    C --> D["Step 3: Legacy vs Evidence Contrast"]
    D --> E["Step 4: Edge-Case Safeguards"]
    E --> F["Step 5: Explainability & Diagnostics"]
```

---

### Step 1: Run the Isolated Algorithmic Test Suite
Demonstrate that the mathematical engine passes all 26 rigorous unit tests covering invariance, scoring, duration pooling, metrics, and diagnostics.

**Command:**
```powershell
python ..\tests\pilot\test_stage_5e2_pilot.py
```

**Talking Points:**
- **Execution Time:** Runs in ~0.03 seconds in pure memory without network latency or database overhead.
- **26 Passed Tests across 5 Test Groups:**
  - *Group A (Invariance & Flags):* Proves that switching to evidence-based scoring causes zero drift on Components A, B, and C (Skills, Responsibilities, Tools).
  - *Group B (Scoring Edge Cases):* Proves saturation at target tenure, linear damping below target, and Rule 10 zeroing.
  - *Group C (Duration Pooling):* Proves that overlapping roles are pooled using time-sliced intervals, preventing double-counting.
  - *Group D (IR Metrics Engine):* Proves Precision@K, NDCG@K, Spearman $\rho$, and tie-rate calculations against exhaustive denominators.
  - *Group E (Diagnostics & Provenance):* Proves structured diagnostic generation for missing dates, inverted dates, and Gate 1 Rule C.

---

### Step 2: Showcase the 4-Component Scoring Architecture
Explain how TalentAI breaks down candidate evaluation into transparent, weighted categories rather than relying on an opaque single-score LLM.

**Architecture Breakdown:**
- **Component A (Required Skills — 25%):** Cosine semantic similarity across core required technical skills.
- **Component B (Responsibilities — 30%):** Alignment between candidate work achievements and core job duties.
- **Component C (Tools & Technologies — 10%):** Direct and semantic match across developer tools, frameworks, and platforms.
- **Component D (Experience Relevance — 35%):** 
  - *Legacy Model:* Assigns static categorical buckets ($0, 40, 70, 100$).
  - *Evidence-Based Model:* $E = 100 \times S_{\text{agg}} \times D$
    - $S_{\text{agg}}$: Aggregate semantic match in preferred domains ($0.0$ to $1.0$).
    - $D$: Duration factor, $D = \min(1.0, Y_{\text{cand}} / Y_{\text{target}})$.
- **Final Score Formula:**
  $$\text{Final Score} = 0.25 A + 0.30 B + 0.10 C + 0.35 D$$

---

### Step 3: Demonstrate Legacy vs. Evidence Scoring Contrast
Demonstrate how the evidence-based formula resolves score ties and prevents single-domain precision collapse using synthetic profiles.

**Interactive Python Demonstration Script:**
Run this command from `backend/`:
```powershell
python -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, '../tests/pilot')
from app.ranking.ranking_service import RankingEngine
from fixtures import CANDIDATE_01_SENIOR, CANDIDATE_05_MID, CANDIDATE_10_NO_RELEVANCE, JD_01_SENIOR_BACKEND

leg_engine = RankingEngine(use_evidence_based_experience=False)
evi_engine = RankingEngine(use_evidence_based_experience=True)

profiles = [('Senior Backend (Full Tenure)', CANDIDATE_01_SENIOR),
            ('Mid Backend (Partial Tenure)', CANDIDATE_05_MID),
            ('Accountant (Zero Relevance)', CANDIDATE_10_NO_RELEVANCE)]

print(f'{'Candidate Profile':<32} | {'Legacy Exp':<10} | {'Evidence Exp':<12} | {'Legacy Final':<12} | {'Evidence Final':<14}')
print('-' * 90)
for label, cand in profiles:
    r_leg = leg_engine.rank_candidates(JD_01_SENIOR_BACKEND, [cand])[0]
    r_evi = evi_engine.rank_candidates(JD_01_SENIOR_BACKEND, [cand])[0]
    e_leg = r_leg.breakdown['experience_relevance'].score
    e_evi = r_evi.breakdown['experience_relevance'].score
    print(f'{label:<32} | {e_leg:<10.1f} | {e_evi:<12.1f} | {r_leg.final_score:<12.2f} | {r_evi.final_score:<14.2f}')
"
```

**Talking Points:**
- **Tenure Saturation (Candidate #1):** With 8.0 years verified against an 8.0y target, $D = 1.000$, yielding full experience credit ($E = 88.0$).
- **Proportional Damping (Candidate #5):** With 5.0 years verified against an 8.0y target, $D = 5.0/8.0 = 0.625$. Evidence score dampens proportionally ($E = 55.0$), whereas Legacy assigned a flat discrete score.
- **Rule 10 Zeroing (Candidate #10):** With zero relevant backend experience, Evidence strictly zeros experience credit ($E = 0.0$), preventing unqualified candidates from ranking high on peripheral skills alone.
- **Tie Resolution:** The continuous evidence calculation eliminates artificial score clustering, reducing top-5 ties by 54.2%.

---

### Step 4: Demonstrate Edge-Case Safeguards & Diagnostics
Show how TalentAI protects against corrupted, inverted, or missing resume dates.

**Interactive Python Demonstration Script:**
Run this command from `backend/`:
```powershell
python -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, '../tests/pilot')
from app.ranking.ranking_service import RankingEngine
from fixtures import CANDIDATE_16_MISSING_DATES, CANDIDATE_17_INVERTED_DATES, JD_01_SENIOR_BACKEND

engine = RankingEngine(use_evidence_based_experience=True)
for label, cand in [('Candidate #16 (Missing Dates)', CANDIDATE_16_MISSING_DATES),
                    ('Candidate #17 (Inverted Dates)', CANDIDATE_17_INVERTED_DATES)]:
    res = engine.rank_candidates(JD_01_SENIOR_BACKEND, [cand])[0]
    exp = res.breakdown['experience_relevance']
    print(f'{label}:')
    print(f'  - Experience Score: {exp.score}')
    print(f'  - Diagnostic Notice: {exp.metadata.get(\"diagnostic_notice\", \"N/A\")}')
    print(f'  - Explanation: {res.explanation}')
"
```

**Talking Points:**
- **Missing Dates:** Rather than crashing or guessing tenure, the engine assigns $D = 0.000, E = 0.00$ and flags `diagnostic_notice: "missing_dates"`.
- **Inverted Dates:** When a resume contains anomalous dates (e.g., Start: 2024, End: 2021), the engine detects chronological invalidity, assigns $D = 0.000, E = 0.00$, and flags `invalid_date_range`.
- **Full Traceability:** The candidate's semantic capability is preserved in the evidence payload, ensuring human reviewers understand *why* duration credit was zeroed.

---

### Step 5: Review Explainability & Candidate Drawer Payload
Showcase the rich JSON diagnostic payload that powers the recruiter UI.

**Demonstration Code:**
```powershell
python -c "
import sys, json; sys.path.insert(0, '.'); sys.path.insert(0, '../tests/pilot')
from app.ranking.ranking_service import RankingEngine
from fixtures import CANDIDATE_01_SENIOR, JD_01_SENIOR_BACKEND

engine = RankingEngine(use_evidence_based_experience=True)
res = engine.rank_candidates(JD_01_SENIOR_BACKEND, [CANDIDATE_01_SENIOR])[0]

output = {
    'candidate_id': res.candidate_id,
    'final_score': res.final_score,
    'breakdown': {k: v.score for k, v in res.breakdown.items()},
    'experience_diagnostics': res.breakdown['experience_relevance'].metadata
}
print(json.dumps(output, indent=2))
"
```

**Talking Points:**
- **Transparent Breakdown:** Recruiter sees exact point contributions for Skills, Responsibilities, Tools, and Experience.
- **Audit Provenance:** Includes verified tenure, target tenure, saturation factor, and domain similarity score.

---

## 4. Concluding the Demonstration

1. Confirm that no background processes or servers remain running.
2. Reiterate that:
   - All demonstrated profiles were synthetic.
   - The production feature flag `USE_EVIDENCE_BASED_EXPERIENCE` remains `False`.
   - Real-data validation is pending formal organizational and privacy approvals.
