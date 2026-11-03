# TalentAI — Viva & Oral Defense Q&A Guide

**Project:** TalentAI — AI Resume Shortlister  
**Document:** Viva / Oral Defense Questions & Answers (`project_closeout/VIVA_QA.md`)  
**Date:** 2026-10-31  
**Audience:** Technical Reviewers, Academic Evaluators, and Viva Examiners  
**Core Principles:** Technical accuracy, explainability, ethical AI guardrails, and compliance transparency.

---

## Group 1: High-Level Concepts & Project Motivation

### Q1: What problem does TalentAI solve?
**A:** Traditional Applicant Tracking Systems (ATS) rely on simple keyword matching (e.g., searching for the exact string `"React"`). If a candidate writes `"React.js"` or describes building reactive user interfaces using component-driven state architecture, keyword systems frequently reject them. Conversely, unqualified candidates can "game" keyword filters by stuffing buzzwords into hidden text.  
TalentAI replaces keyword filtering with **semantic matching and explainable multi-component ranking**, evaluating technical depth, responsibilities, tools, and verified tenure against explicit Job Description criteria.

### Q2: Why is TalentAI called a "decision-support" tool rather than an automated hiring system?
**A:** In high-stakes employment contexts, automated decision-making (AEDT) creates severe ethical and legal risks. TalentAI is explicitly designed as a **decision-support tool for candidate shortlisting**. It surfaces structured evidence, breaks down alignment across four transparent categories, and flags diagnostic alerts. It never makes hiring, rejection, or interview decisions; final employment determinations remain under the exclusive authority of human recruiters and hiring managers.

### Q3: Why not just send the resume and Job Description to a public LLM like ChatGPT?
**A:** Three major reasons:
1. **Privacy & Regulatory Compliance:** Sending candidate resumes containing personal names, emails, and employment history to public third-party APIs violates data protection laws (such as GDPR, CCPA, and NYC Local Law 144) and candidate confidentiality.
2. **Hallucination & Inconsistency:** LLMs given raw prompts produce non-deterministic scores, hallucinate qualifications, and exhibit subtle biases.
3. **Auditability & Explainability:** A single LLM score cannot be mathematically deconstructed. TalentAI uses deterministic mathematical formulas ($0.25A + 0.30B + 0.10C + 0.35D$) and local embeddings (`qwen3:8b`), ensuring 100% reproducible and transparent scoring.

---

## Group 2: Semantic Matching & Embedding Fundamentals

### Q4: How does semantic matching work in TalentAI?
**A:** TalentAI converts text (e.g., candidate skill descriptions and Job Description requirements) into high-dimensional vector embeddings using a local embedding model. It then calculates the **cosine similarity** between these vectors:
$$\text{Cosine Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$
Cosine similarity measures the angle between the two concepts in vector space. Synonyms or closely related technical terms (e.g., `"PostgreSQL"` and `"relational database"`, or `"Kubernetes"` and `"container orchestration"`) produce high similarity scores even when the exact words differ.

### Q5: What are the four ranking components and why are they weighted this way?
**A:** TalentAI scores candidates across four transparent categories:
- **Component A: Required Skills (Weight 25% / 0.25):** Core technical competencies explicitly required by the JD.
- **Component B: Responsibilities (Weight 30% / 0.30):** Past project achievements and day-to-day duties matching JD requirements.
- **Component C: Tools & Technologies (Weight 10% / 0.10):** Specific developer tooling, libraries, and platforms.
- **Component D: Experience Relevance (Weight 35% / 0.35):** Demonstrated depth and verified duration in the preferred technical domain.

**Rationale for Weights:** Experience Relevance (35%) and Responsibilities (30%) carry the highest weights because practical tenure and proven job execution are the strongest technical predictors of candidate alignment, whereas specific tools (10%) can be learned relatively quickly on the job.

---

## Group 3: The Evidence-Based Experience Formula

### Q6: How does evidence-based experience scoring differ from legacy categorical scoring?
**A:** 
- **Legacy Categorical Scoring:** Assigns discrete bucket scores ($0, 40, 70, 100$) based on generic keyword presence. This creates severe score clustering (ties) and allows unqualified candidates with shallow tenure to receive high scores.
- **Evidence-Based Scoring:** Computes continuous experience credit:
  $$E = 100 \times S_{\text{agg}} \times D$$
  where $S_{\text{agg}}$ is the candidate's aggregate semantic similarity in the target domain, and $D$ is the duration factor.

### Q7: What is the Duration Factor ($D$) and how is it calculated?
**A:** The duration factor scales candidate credit based on verified tenure relative to the JD target:
$$D = \min\left(1.0, \frac{Y_{\text{cand}}}{Y_{\text{target}}}\right)$$
- If a candidate meets or exceeds target tenure ($Y_{\text{cand}} \ge Y_{\text{target}}$), $D = 1.000$ (Tenure Saturation).
- If a candidate has partial tenure ($Y_{\text{cand}} < Y_{\text{target}}$), $D$ dampens proportionally (e.g., 4 years out of 8 years yields $D = 0.500$).
- If a candidate has zero verified tenure, $D = 0.000$ and $E = 0.00$.

### Q8: What is "duration pooling" and why is it necessary?
**A:** Candidates frequently hold concurrent or overlapping positions (e.g., freelancing while working full-time, or overlapping consulting roles). If you simply sum up the durations of each role, a candidate working two concurrent 1-year jobs would falsely claim 2 years of experience in a single calendar year.  
TalentAI uses a **time-sliced duration pooling algorithm** that merges overlapping calendar intervals, calculating only true, non-overlapping calendar elapsed time ($Y_{\text{cand}}$).

---

## Group 4: Edge Cases & Diagnostic Safeguards

### Q9: How does TalentAI handle resumes with missing or inverted dates?
**A:** Rather than crashing or guessing dates, TalentAI enforces strict diagnostic safeguards:
- **Missing Dates:** If a candidate profile lacks start or end dates, the engine assigns $D = 0.000, E = 0.00$ and attaches the diagnostic notice `missing_dates`.
- **Inverted Dates:** If a start date is chronologically after an end date (e.g., Start: 2024, End: 2021), the engine assigns $D = 0.000, E = 0.00$ and attaches `invalid_date_range`.
- **Evidence Preservation:** In both cases, the candidate's semantic skill match ($S_{\text{agg}}$) is preserved in the audit payload so human recruiters understand *why* duration credit was zeroed.

### Q10: What is Gate 1 Rule C (Unbounded Experience)?
**A:** When a Job Description does not specify any minimum or maximum years of experience (an "unbounded" role), duration cannot be evaluated fairly against an arbitrary number.  
Under Gate 1 Rule C, the duration factor is explicitly zeroed ($D = 0.000, E = 0.00$) with diagnostic status `"unspecified"`. Candidates are ranked strictly on their technical competence, responsibilities, and tools (Components A–C), preventing arbitrary tenure penalties.

---

## Group 5: Synthetic Validation & Benchmark Metrics

### Q11: What were the results of the broad synthetic benchmark (Stage 5E.3.3)?
**A:** Evaluated across **12 Job Descriptions and 240 synthetic candidate profiles**:
- **Precision@3:** Evidence Engine achieved **1.0000** vs. Legacy Engine **0.9445** (+5.55%).
- **Precision@5:** Evidence Engine achieved **1.0000** vs. Legacy Engine **0.9667** (+3.33%).
- **NDCG@3:** Evidence Engine achieved **1.0000** vs. Legacy Engine **0.9441** (+5.59%).
- **NDCG@5:** Evidence Engine achieved **1.0000** vs. Legacy Engine **0.9596** (+4.04%).
- **Spearman Rank Correlation ($\rho$):** Evidence Engine achieved **0.9156** vs. Legacy Engine **0.8404** (+0.0751 delta against human consensus).
- **Top-5 Score Ties:** Reduced from **0.4000** to **0.1833** (a **54.2% reduction**).

### Q12: What was the "single-domain precision collapse" observed in the legacy engine?
**A:** In specialized single-domain roles (`JD-BROAD-10: Embedded Systems` and `JD-BROAD-11: SDET Automation`), the legacy engine suffered severe precision collapse: **Precision@3 dropped to 0.6667** (1 out of every 3 top candidates was non-relevant).  
This happened because unqualified candidates matching generic peripheral keywords (e.g., Git, Linux) received high scores. The Evidence Engine completely solved this ($P@3 = 1.0000$) by multiplying domain relevance by verified domain tenure ($S_{\text{agg}} \times D$).

### Q13: What is NDCG and Spearman's Rho, and why are they used?
**A:**
- **NDCG (Normalized Discounted Cumulative Gain):** Measures ranking quality, heavily penalizing models that place highly qualified candidates lower down the shortlist. An NDCG of 1.0000 means the most qualified candidates appear at the top.
- **Spearman's Rank Correlation ($\rho$):** Measures the monotonic alignment between AI candidate rankings and human ground-truth rankings. A correlation of $\rho = 0.9156$ indicates near-perfect ranking agreement with human consensus.

---

## Group 6: Privacy, Governance & Readiness Gate

### Q14: Why is real-data validation currently blocked?
**A:** Real-data validation is blocked at the **Stage 5E.4.0 Readiness Gate** because candidate privacy and data protection are non-negotiable. Before real resumes can be accessed, **10 mandatory prerequisites** must be formally satisfied (including Data Owner authorization, a documented legal processing basis, a DPIA, and a certified de-identification toolchain). Currently, all 10 prerequisites are **Pending**.

### Q15: Why is removing names alone insufficient for resume de-identification?
**A:** Research shows that combinations of **quasi-identifiers** (such as a unique job title, specialized technology stack, company domain, geographic city, and exact graduation year) can uniquely re-identify individuals (up to 87% re-identification rate via LinkedIn or GitHub linkage attacks). De-identification requires a multi-pass pipeline that redacts direct PII, suppresses graduation years, and generalizes company names to broad industry sectors.

### Q16: What is the current state of the production feature flag?
**A:** The global feature flag `USE_EVIDENCE_BASED_EXPERIENCE` is strictly set to **`False`** in `ranking_config.py`. Production continues to utilize the legacy scoring model. The evidence-based engine will only be considered for production activation after real-data validation (Stage 5E.4) and executive go/no-go review (Stage 5E.5).

### Q17: What are the main limitations of the project at this stage?
**A:**
1. **Synthetic Data Homogeneity:** Evaluations were performed on structured synthetic profiles; real resumes contain more noise, OCR errors, and non-standard chronology.
2. **Pending Legal Approvals:** Formal authorizations from corporate legal and privacy officers are pending.
3. **De-Identification Toolchain:** The proposed 4-pass de-identification architecture has been specified in governance protocols, but has not yet been built or certified in code.
