# TalentAI — Legacy vs. Evidence-Based Experience Scoring Evaluation Report

**Project:** TalentAI — AI Resume Shortlister  
**Document:** Scoring System Evaluation Report (`project_closeout/SCORING_SYSTEM_EVALUATION_REPORT.md`)  
**Report date:** 31 October 2026  
**Evaluation basis:** Reported synthetic benchmark results  
**Purpose:** Compare the Legacy scoring system with the new Evidence-Based Experience scoring system and recommend which should be retained.

---

## 1. Executive Summary

TalentAI has two experience-scoring approaches:

- **Legacy Categorical Scoring:** Uses discrete experience categories or duration buckets.
- **Evidence-Based Experience Scoring:** Uses relevant experience evidence, semantic similarity, and duration-based saturation to calculate a continuous experience score.

The reported broad synthetic benchmark shows that the Evidence-Based system performed better than Legacy across the listed information-retrieval metrics. It also reduced the number of candidates tied at the full-cohort level.

However, these results were obtained using synthetic candidate profiles and synthetic job descriptions. They do not establish that the Evidence-Based system is more accurate, fair, or reliable when applied to real resumes.

### Recommendation

**Keep both systems, but use the Evidence-Based system as the preferred system for further evaluation and synthetic demonstrations. Retain Legacy as the stable baseline until real-world validation and required approvals are available.**

Do not declare the new system production-proven based only on synthetic benchmark results.

---

## 2. Scoring System Comparison

| Feature | Legacy Categorical | Evidence-Based Experience |
|---|---|---|
| Experience representation | Discrete categories or duration buckets | Continuous score based on relevant evidence and duration |
| Experience relevance | More dependent on categorical rules | Considers relevance to the job description |
| Duration handling | Category-based | Duration saturation and target-aware handling |
| Explainability | Explains categorical score | Can show relevant experience evidence and duration diagnostics |
| Score differentiation | May produce more ties | Reported to produce fewer full-cohort ties |
| Benchmark role | Baseline | New approach under evaluation |

The Evidence-Based system is designed to provide a more detailed representation of experience. Whether this design results in better hiring decisions still requires independent evaluation.

---

## 3. Reported Synthetic Benchmark Results

The broad benchmark report describes 12 synthetic job descriptions and 240 synthetic candidate profiles across six technical strata.

| Metric | Legacy | Evidence-Based | Better reported result |
|---|---:|---:|---|
| Precision@3 | 0.9445 | 1.0000 | Evidence-Based |
| Precision@5 | 0.9667 | 1.0000 | Evidence-Based |
| Recall@5 | 0.3187 | 0.3298 | Evidence-Based |
| NDCG@3 | 0.9441 | 1.0000 | Evidence-Based |
| Spearman rank correlation ($\rho$) | 0.8404 | 0.9156 | Evidence-Based |
| Full-cohort tie rate | 0.0719 | 0.0272 | Evidence-Based: fewer ties |

**Interpretation:** On the reported synthetic benchmark, the Evidence-Based system ranked the constructed relevant candidates more effectively according to the benchmark’s labels. Its ranking correlation with the synthetic ground truth was also higher.

These figures are reproduced from the reported project results. They have not been independently recalculated in this report.

---

## 4. What the Results Do—and Do Not—Prove

### What they support

The reported results support the following limited conclusions:

1. The Evidence-Based system performed better on the reported synthetic benchmark.
2. Its ranking was more aligned with the synthetic ground-truth labels.
3. It produced fewer full-cohort ties.
4. It is a promising approach for further evaluation.

### What they do not prove

The results do not establish:

- Higher accuracy on real resumes.
- Better hiring outcomes or candidate quality.
- Fairness across demographic groups.
- Reliability with OCR errors, unusual resume formats, or ambiguous job titles.
- Validity of the scoring thresholds for real recruitment.
- That the new system should automatically replace Legacy in production.

The synthetic profiles were constructed using standardized archetypes. Real resumes can contain inconsistent dates, overlapping jobs, missing information, unclear responsibilities, and formatting variation. These conditions require additional testing.

---

## 5. Advantages and Limitations

### Legacy system

**Advantages**
- Provides a stable comparison baseline.
- Uses a simpler categorical scoring approach.
- Can be easier to explain at a high level.

**Limitations**
- Discrete experience buckets may hide meaningful differences between candidates.
- Candidates with different evidence may receive similar category-based scores.
- May not represent job-specific experience relevance as precisely.

### Evidence-Based system

**Advantages**
- Uses a continuous experience score.
- Can account for the relevance of experience to the job description.
- Supports more detailed evidence-based explanations.
- Reported lower tie rates and stronger synthetic ranking metrics.

**Limitations**
- More dependent on the quality of extracted resume evidence.
- Semantic similarity and duration assumptions need careful validation.
- More complex to explain and audit.
- Synthetic results do not guarantee real-world performance.
- Incorrect or incomplete extracted data can affect the score.

---

## 6. Which System Should TalentAI Keep?

### Recommended approach: retain both, with different roles

| Use case | Recommended system |
|---|---|
| Synthetic demo | Evidence-Based as the preferred demonstration mode; Legacy retained for comparison |
| Development and testing | Run both systems against the same synthetic fixtures |
| Benchmark evaluation | Compare both using the same ground-truth labels and metrics |
| Current production default | Keep Legacy until the Evidence-Based system is validated and approved |
| Future production decision | Consider Evidence-Based after documented validation, review, and authorization |

This recommendation is based on the reported synthetic evidence and the current project readiness status. It is not a claim that Legacy is more accurate in real-world hiring.

---

## 7. Recommended Next Steps

1. Verify that the original ranking pipeline—not only the synthetic demo—uses the intended Evidence-Based scoring implementation.
2. Keep the production feature flag unchanged until the integration and isolated tests are confirmed.
3. Test both scoring systems on the same synthetic inputs and preserve reproducible results.
4. Review score explanations, missing-date handling, invalid-date handling, and target-experience edge cases.
5. Document the limitations of synthetic validation in the project report and presentation.
6. Consider real-data validation only after the required data-owner, privacy, legal, security, and stakeholder approvals are genuinely obtained.
7. Make any future production scoring change through an explicit, reviewed decision—not solely because the synthetic benchmark is stronger.

---

## 8. Final Conclusion

The reported synthetic benchmark favors the Evidence-Based Experience system over Legacy across the listed ranking metrics. This makes Evidence-Based the stronger candidate for continued development and evaluation.

**The recommended decision is to keep both systems:**

- Keep Evidence-Based as the preferred system for synthetic demonstration and further evaluation.
- Keep Legacy as the production baseline until the new system’s integration, real-world validity, fairness, and governance requirements have been established.

The most accurate conclusion at this stage is:

> “The Evidence-Based Experience scoring system outperformed the Legacy system on the reported synthetic benchmark. Its real-world accuracy and suitability for production recruitment remain unverified and require further authorized validation.”

This conclusion reflects the current evidence without overstating what the synthetic results can demonstrate.
