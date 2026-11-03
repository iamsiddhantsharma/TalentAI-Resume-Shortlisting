# TalentAI Phase 9.3 — Human-Reviewed Ranking Quality Evaluation Protocol

## 1. Overview & Purpose
This document defines the rigorous, reproducible evaluation protocol for assessing whether TalentAI's resume rankings agree with independent human judgments of candidate-to-Job Description (JD) relevance.

> [!IMPORTANT]
> **Ethical & Decision-Support Guardrail**  
> TalentAI scores and rankings measure **semantic and textual alignment with explicit Job Description criteria**. They do **not** represent innate candidate capability, culture fit, interview performance, or a statistical probability of hiring success. TalentAI is a decision-support and candidate-shortlisting tool; it is never an automated decision-maker or hiring authority.

---

## 2. Reviewer Independence & Double-Blind Protocol

1. **Strict Score & Rank Masking**:
   - Reviewers evaluate candidate profiles using only:
     - The explicit Job Description text and criteria.
     - The anonymized candidate resume content.
   - Reviewers are strictly blinded to:
     - TalentAI overall final scores ($0–100$).
     - Component subscores (Skills, Responsibilities, Tools, Experience).
     - Model-generated ranking positions.
     - System-generated explanatory notes or diagnostic text.
2. **Independent Grading**:
   - Evaluator A (Engineering Lead perspective) and Evaluator B (Technical Recruiter perspective) evaluate candidates independently without communication or calibration during the initial scoring round.
   - Each reviewer records their initial grades in the standardized template before any discussion.

---

## 3. Standardized 4-Point Relevance Rubric

Reviewers evaluate **Criteria Relevance** on a 4-point ordinal scale ($0$ to $3$):

| Grade | Classification | Operational Rubric Definition |
| :---: | :--- | :--- |
| **3** | **Exceptional Fit** | Directly matches all/nearly all required skills. Demonstrates explicit, deep project evidence for primary responsibilities and tools. Work history includes direct preferred-domain accomplishments. |
| **2** | **Good / Partial Fit** | Matches core required skills (or close semantic equivalents). Demonstrates solid project/work evidence for several key responsibilities. Background shows relevant domain exposure with minor secondary gaps. |
| **1** | **Marginal Fit** | Matches peripheral skills only. Semantic overlap on core responsibilities is weak, theoretical, or superficial. Lacks relevant industry or domain experience. |
| **0** | **Unqualified / Clean Zero** | Candidate matches zero or negligible required skills. Responsibilities and projects reflect completely unrelated functional areas (e.g., Accountant applying for Machine Learning Scientist). |
| **DEFECT** | **Technical Failure** | Resume file is corrupted, unparseable, truncated, or timed out. **Must NOT be assigned Grade 0.** Must be flagged as a technical defect. |

---

## 4. Critical Scoring Distinction: Relevance vs. Duration

As established in TalentAI's Phase 6 scoring architecture:
1. **Separation of Duration Diagnostic from Qualitative Relevance**:
   - The $0–100$ relevance score measures qualitative alignment across the 4 categories (Required Skills 25%, Responsibilities 30%, Tools 10%, Experience Relevance 35%).
   - Minimum experience duration is evaluated as an **independent diagnostic status** (`minimum_duration_satisfied: bool`).
2. **Reviewer Instruction**:
   - Reviewers must assess **Criteria Relevance** based on depth, capability, and domain fit without penalizing relevance solely because the candidate's total calendar duration falls below the minimum years threshold.
   - Reviewers record `Duration Satisfied (Yes/No)` as an independent column.

---

## 5. Disagreement Resolution & Adjudication Protocol

1. **Inter-Rater Reliability Assessment**:
   - Prior to adjudication, calculate **Linear and Quadratic Weighted Cohen's Kappa ($\kappa_w$)** using the raw initial grades of Reviewer A and Reviewer B.
2. **Minor Discrepancy ($|Grade_A - Grade_B| = 1$)**:
   - For adjacent grades (e.g., Grade 3 vs. Grade 2, or Grade 2 vs. Grade 1), reviewers consult the rubric to determine whether specific project evidence justifies the higher score.
   - If consensus is reached, the agreed grade is recorded. If split evenly, the consensus is recorded as the arithmetic mean ($2.5$ or $1.5$) for continuous analysis or rounded per documented convention.
3. **Major Discrepancy ($|Grade_A - Grade_B| \ge 2$)**:
   - Where ratings diverge by 2 or more points (e.g., Grade 1 vs. Grade 3), an independent third adjudicator conducts an in-depth review of cited evidence to establish the binding ground-truth label.
4. **Provenance Tracking**:
   - Both initial reviewer grades are preserved in the evaluation record alongside the final adjudicated label.

---

## 6. Evaluation Metrics

1. **Inter-Reviewer Agreement**:
   - Weighted Cohen's Kappa: $\kappa_w \ge 0.70$ target.
2. **Ranking Agreement with Adjudicated Ground Truth**:
   - **Tie-Aware NDCG@K ($K \in \{3, 5\}$)**: Evaluates quality while accounting for score ties.
   - **Precision@K ($K \in \{3, 5\}$)**: Evaluates the proportion of shortlisted candidates with adjudicated Grade $\ge 2$.
   - **Spearman's Rank Correlation ($\rho$) & Kendall's Tau-b ($\tau_b$)**: Measures monotonic rank agreement between AI scores and human consensus.
   - **Incomplete Candidate Separation Rate (ICSR)**: Target $100.0\%$ (all technical defects diverted to `unranked` with `final_score: null`).

---

## 7. Privacy, Confidentiality & Ethical Safeguards

1. **Synthetic Benchmark Prioritization**:
   - All evaluation profiles in this benchmark are 100% synthetic to ensure reproducibility and eliminate PII risks.
2. **Real Resume Data Governance (Future Deployment Gate)**:
   - Real candidate resumes must never be processed without written, informed consent for algorithmic evaluation.
   - Any non-synthetic resumes must undergo full PII de-identification (names, emails, phones, postal addresses, demographic indicators, and graduation years redacted).
   - Resumes must be processed locally with ephemeral session storage; zero resume data may be sent to public external LLMs or third-party logging platforms.
