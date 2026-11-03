"""
TalentAI — Stage 5E.2: Synthetic Pilot Evaluation Fixtures

This module contains pure in-memory, synthetic fixtures for evaluating legacy
vs. evidence-based experience ranking across 3 Job Descriptions and 24 candidate profiles.

Privacy & Safety Invariants:
- 100% synthetic names, fictional company names, and generated work histories.
- Zero production candidate data, zero PII, zero real resumes.
- Pure in-memory data structures (no database records or external dependencies).
"""

from copy import deepcopy
from typing import Any

from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)

# ==============================================================================
# 1. SYNTHETIC JOB DESCRIPTIONS (COHORT OF 3)
# ==============================================================================

JD_PILOT_01 = JobDescriptionObject(
    required_skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
    responsibilities=[
        "Design and implement scalable microservices APIs",
        "Optimize SQL database queries and migrations",
        "Configure containerized cloud deployments",
    ],
    tools_and_technologies=["Docker", "Kubernetes", "PostgreSQL"],
    experience_requirements=[
        ExperienceRequirement(
            minimum_years=3.0,
            maximum_years=6.0,
            preferred_domains=["Fintech", "Cloud Systems"],
        )
    ],
)

JD_PILOT_02 = JobDescriptionObject(
    required_skills=["Python", "PyTorch", "Transformers", "SQL"],
    responsibilities=[
        "Train and fine-tune foundation models",
        "Optimize low-latency transformer inference pipelines",
        "Deploy distributed model serving infrastructure",
    ],
    tools_and_technologies=["PyTorch", "Ray", "Triton"],
    experience_requirements=[
        ExperienceRequirement(
            minimum_years=4.0,
            maximum_years=None,
            preferred_domains=["Natural Language Processing"],
        )
    ],
)

JD_PILOT_03 = JobDescriptionObject(
    required_skills=["Go", "Kubernetes", "Linux", "gRPC"],
    responsibilities=[
        "Architect multi-region Kubernetes clusters",
        "Engineer high-throughput messaging topologies",
        "Diagnose Linux kernel-level network performance bottlenecks",
    ],
    tools_and_technologies=["Kubernetes", "Prometheus", "Kafka"],
    experience_requirements=[
        ExperienceRequirement(
            minimum_years=None,
            maximum_years=None,
            preferred_domains=["Cloud Infrastructure", "Distributed Storage"],
        )
    ],
)

JOB_DESCRIPTIONS: dict[str, JobDescriptionObject] = {
    "JD-Pilot-01": JD_PILOT_01,
    "JD-Pilot-02": JD_PILOT_02,
    "JD-Pilot-03": JD_PILOT_03,
}


# ==============================================================================
# 2. STANDARDIZED NON-EXPERIENCE COMPONENT GENERATOR
# ==============================================================================

def _make_standard_components_a_b_c(jd_id: str, skills_ratio: float = 1.0, resp_sim: float = 0.85, tools_sim: float = 0.88) -> tuple[dict, dict]:
    """Generates standardized ExactMatching and SemanticRetrieval payloads."""
    if jd_id == "JD-Pilot-01":
        skills = ["Python", "FastAPI", "Docker", "PostgreSQL"]
        resps = ["Design and implement scalable microservices APIs", "Optimize SQL database queries and migrations", "Configure containerized cloud deployments"]
        tools = ["Docker", "Kubernetes", "PostgreSQL"]
    elif jd_id == "JD-Pilot-02":
        skills = ["Python", "PyTorch", "Transformers", "SQL"]
        resps = ["Train and fine-tune foundation models", "Optimize low-latency transformer inference pipelines", "Deploy distributed model serving infrastructure"]
        tools = ["PyTorch", "Ray", "Triton"]
    else:  # JD-Pilot-03
        skills = ["Go", "Kubernetes", "Linux", "gRPC"]
        resps = ["Architect multi-region Kubernetes clusters", "Engineer high-throughput messaging topologies", "Diagnose Linux kernel-level network performance bottlenecks"]
        tools = ["Kubernetes", "Prometheus", "Kafka"]

    # Exact matching
    matched_count = int(round(len(skills) * skills_ratio))
    skill_matches = [
        {"required_skill": s, "matched": idx < matched_count}
        for idx, s in enumerate(skills)
    ]
    exact_matching = {
        "total_required_skills": len(skills),
        "matched_required_skills": matched_count,
        "unmatched_required_skills": len(skills) - matched_count,
        "matches": skill_matches,
    }

    # Semantic retrieval
    semantic_retrieval = {
        "top_k": 5,
        "responsibilities_retrieval": {
            "top_k": 5,
            "results": [
                {
                    "jd_item_index": idx,
                    "jd_text": r,
                    "matches": [
                        {"similarity": resp_sim, "resume_text": f"Synthetic evidence for {r}", "resume_section": "Experience"}
                    ],
                }
                for idx, r in enumerate(resps)
            ],
        },
        "tools_and_technologies_retrieval": {
            "top_k": 5,
            "results": [
                {
                    "jd_item_index": idx,
                    "jd_text": t,
                    "matches": [
                        {"similarity": tools_sim, "resume_text": f"Synthetic evidence for {t}", "resume_section": "Skills"}
                    ],
                }
                for idx, t in enumerate(tools)
            ],
        },
    }

    return exact_matching, semantic_retrieval


# ==============================================================================
# 3. 24 SYNTHETIC CANDIDATE PROFILES
# ==============================================================================

SYNTHETIC_CANDIDATE_FIXTURES: dict[str, dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # JD-Pilot-01 Cohort (Bounded 3.0 - 6.0 yrs, Fintech + Cloud Systems)
    # --------------------------------------------------------------------------
    "CAND-01": {
        "name": "Alex Mercer (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Lead Cloud Architect (Tenure Saturation & Dual Domain)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 87.00},
        "skills_ratio": 1.0, "resp_sim": 0.88, "tools_sim": 0.90,
        "experience_matching": {
            "duration_factor": 1.000,
            "relevant_duration_years": 7.0,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.870,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Principal Cloud Architect",
                    "company": "Apex Fintech Solutions (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Fintech", "Cloud Systems"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 7.0,
                    "semantic_similarity": 0.96,
                    "calibrated_similarity": 0.89,
                    "relevant_work_summary": "Architected high-throughput cloud payment rails and container infrastructure.",
                    "start_date": "2017-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-02": {
        "name": "Jordan Lee (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Mid-Level Cloud Dev (Proportional Duration Damping)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 40.50},
        "skills_ratio": 1.0, "resp_sim": 0.85, "tools_sim": 0.86,
        "experience_matching": {
            "duration_factor": 0.500,
            "relevant_duration_years": 3.0,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.810,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Cloud Software Engineer",
                    "company": "Digital Ledger Labs (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Fintech", "Cloud Systems"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 3.0,
                    "semantic_similarity": 0.93,
                    "calibrated_similarity": 0.81,
                    "relevant_work_summary": "Developed containerized microservices and automated payment reconciliations.",
                    "start_date": "2021-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-03": {
        "name": "Taylor Morgan (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Fintech Specialist (Single Domain, Unsupported Zero-Fill)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 50.0, "evidence_exp": 43.00},
        "skills_ratio": 0.75, "resp_sim": 0.82, "tools_sim": 0.80,
        "experience_matching": {
            "duration_factor": 1.000,
            "relevant_duration_years": 6.5,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.430,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Quantitative Banking Engineer",
                    "company": "Heritage Trust Capital (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Fintech"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 6.5,
                    "semantic_similarity": 0.95,
                    "calibrated_similarity": 0.86,
                    "relevant_work_summary": "Implemented quantitative banking ledger engines without cloud infra.",
                    "start_date": "2017-06-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-04": {
        "name": "Casey Rivera (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Multi-Role Fintech & Cloud Dev (Max Similarity per Domain)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 82.50},
        "skills_ratio": 1.0, "resp_sim": 0.88, "tools_sim": 0.88,
        "experience_matching": {
            "duration_factor": 1.000,
            "relevant_duration_years": 6.5,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.825,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Senior Fintech Developer",
                    "company": "SecurePay Systems (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Fintech"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 3.5,
                    "semantic_similarity": 0.95,
                    "calibrated_similarity": 0.85,
                    "relevant_work_summary": "Engineered automated transactional gateways and fraud filters.",
                    "start_date": "2020-07-01",
                    "end_date": "2024-01-01",
                },
                {
                    "experience_index": 1,
                    "role": "Junior Financial Analyst & Programmer",
                    "company": "First Capital Trust (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Fintech"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 3.0,
                    "semantic_similarity": 0.89,
                    "calibrated_similarity": 0.68,
                    "relevant_work_summary": "Wrote financial data ingestion scripts.",
                    "start_date": "2017-06-01",
                    "end_date": "2020-06-01",
                },
                {
                    "experience_index": 2,
                    "role": "Cloud DevOps Engineer",
                    "company": "CloudNet Services (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Systems"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 3.0,
                    "semantic_similarity": 0.93,
                    "calibrated_similarity": 0.80,
                    "relevant_work_summary": "Deployed AWS and Kubernetes microservices.",
                    "start_date": "2020-07-01",
                    "end_date": "2023-07-01",
                },
            ],
        },
    },
    "CAND-05": {
        "name": "Riley Vance (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Concurrent / Overlapping Roles (Time-Sliced Deduplication)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 41.00},
        "skills_ratio": 1.0, "resp_sim": 0.84, "tools_sim": 0.85,
        "experience_matching": {
            "duration_factor": 0.500,
            "relevant_duration_years": 3.0,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.820,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Full-Time Cloud Engineer",
                    "company": "Enterprise Cloud Inc (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Systems"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 3.0,
                    "semantic_similarity": 0.94,
                    "calibrated_similarity": 0.82,
                    "relevant_work_summary": "Constructed cloud infrastructure and cluster policies.",
                    "start_date": "2021-01-01",
                    "end_date": "2024-01-01",
                },
                {
                    "experience_index": 1,
                    "role": "Concurrent Fintech Consultant",
                    "company": "Boutique Payments LLC (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Fintech"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 2.0,
                    "semantic_similarity": 0.94,
                    "calibrated_similarity": 0.82,
                    "relevant_work_summary": "Consulted on payment gateway integrations during nights and weekends.",
                    "start_date": "2022-01-01",
                    "end_date": "2024-01-01",
                },
            ],
        },
    },
    "CAND-06": {
        "name": "Morgan Bailey (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Missing Employment Dates (Strict Safeguard)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 0.00},
        "skills_ratio": 1.0, "resp_sim": 0.86, "tools_sim": 0.86,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 0.0,
            "diagnostic_status": "missing_dates",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.850,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Fintech Platform Architect",
                    "company": "Payment Core LLC (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Fintech", "Cloud Systems"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 0.0,
                    "semantic_similarity": 0.95,
                    "calibrated_similarity": 0.85,
                    "relevant_work_summary": "Architected scalable microservices and transactional banking infrastructure.",
                    "start_date": None,
                    "end_date": None,
                }
            ],
        },
    },
    "CAND-07": {
        "name": "Samira Khan (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Peripheral Software Dev (Weak Alignment & Marginal Grade)",
        "human_ground_truth": {"grade": 1, "label": "Marginal Fit", "r1": 1, "r2": 1},
        "expected_scores": {"legacy_exp": 50.0, "evidence_exp": 43.33},
        "skills_ratio": 0.50, "resp_sim": 0.72, "tools_sim": 0.70,
        "experience_matching": {
            "duration_factor": 0.6667,
            "relevant_duration_years": 4.0,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.650,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Web Shop Programmer",
                    "company": "Commerce Portals (Synthetic)",
                    "decision": "AMBIGUOUS",
                    "relevant": True,
                    "matched_domains": ["Fintech", "Cloud Systems"],
                    "relevance_ratio": 0.5,
                    "relevant_duration_years": 4.0,
                    "semantic_similarity": 0.88,
                    "calibrated_similarity": 0.65,
                    "relevant_work_summary": "Maintained shopping cart checkout scripts and basic server configs.",
                    "start_date": "2020-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-08": {
        "name": "Devon Hayes (Synthetic)",
        "target_jd": "JD-Pilot-01",
        "archetype": "Irrelevant Background (Graphic Designer, Rule 10 Zeroing)",
        "human_ground_truth": {"grade": 0, "label": "Unqualified / Irrelevant", "r1": 0, "r2": 0},
        "expected_scores": {"legacy_exp": 0.00, "evidence_exp": 0.00},
        "skills_ratio": 0.0, "resp_sim": 0.50, "tools_sim": 0.50,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 0.0,
            "diagnostic_status": "no_relevant_experience",
            "saturation_target_years": 6.0,
            "range_status": "bounded",
            "aggregated_similarity": 0.000,
            "minimum_years": 3.0,
            "maximum_years": 6.0,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Lead Graphic Designer",
                    "company": "Creative Visions Studio (Synthetic)",
                    "decision": "IRRELEVANT",
                    "relevant": False,
                    "matched_domains": [],
                    "relevance_ratio": 0.0,
                    "relevant_duration_years": 0.0,
                    "semantic_similarity": 0.0,
                    "calibrated_similarity": 0.0,
                    "relevant_work_summary": None,
                    "start_date": "2016-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },

    # --------------------------------------------------------------------------
    # JD-Pilot-02 Cohort (Min-Only 4.0 yrs, NLP)
    # --------------------------------------------------------------------------
    "CAND-09": {
        "name": "Dr. Elena Rostova (Synthetic)",
        "target_jd": "JD-Pilot-02",
        "archetype": "Principal NLP Researcher (Min-Only Saturation)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 92.00},
        "skills_ratio": 1.0, "resp_sim": 0.92, "tools_sim": 0.92,
        "experience_matching": {
            "duration_factor": 1.000,
            "relevant_duration_years": 5.5,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.920,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Staff NLP Research Scientist",
                    "company": "Cognitive AI Labs (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 5.5,
                    "semantic_similarity": 0.97,
                    "calibrated_similarity": 0.92,
                    "relevant_work_summary": "Trained and deployed billion-parameter transformer foundation models.",
                    "start_date": "2018-07-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-10": {
        "name": "Liam Chen (Synthetic)",
        "target_jd": "JD-Pilot-02",
        "archetype": "Junior ML Engineer (Min-Only Proportional Damping)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 31.50},
        "skills_ratio": 1.0, "resp_sim": 0.85, "tools_sim": 0.82,
        "experience_matching": {
            "duration_factor": 0.375,
            "relevant_duration_years": 1.5,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.840,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Junior Machine Learning Engineer",
                    "company": "Neural Horizons (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 1.5,
                    "semantic_similarity": 0.94,
                    "calibrated_similarity": 0.84,
                    "relevant_work_summary": "Fine-tuned BERT classification models and tokenization pipelines.",
                    "start_date": "2022-07-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-11": {
        "name": "Marcus Brody (Synthetic)",
        "target_jd": "JD-Pilot-02",
        "archetype": "Computer Vision Engineer (Domain Mismatch for NLP)",
        "human_ground_truth": {"grade": 1, "label": "Marginal Fit", "r1": 1, "r2": 1},
        "expected_scores": {"legacy_exp": 0.00, "evidence_exp": 0.00},
        "skills_ratio": 0.50, "resp_sim": 0.70, "tools_sim": 0.70,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 0.0,
            "diagnostic_status": "no_relevant_experience",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.000,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Senior Computer Vision Engineer",
                    "company": "VisionMetrics Corp (Synthetic)",
                    "decision": "IRRELEVANT",
                    "relevant": False,
                    "matched_domains": ["Computer Vision"],
                    "relevance_ratio": 0.0,
                    "relevant_duration_years": 0.0,
                    "semantic_similarity": 0.0,
                    "calibrated_similarity": 0.0,
                    "relevant_work_summary": "Trained YOLO object detection networks for drone footage.",
                    "start_date": "2019-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-12": {
        "name": "Avery Brooks (Synthetic)",
        "target_jd": "JD-Pilot-02",
        "archetype": "Multi-Role Data Scientist (Multi-Role Max Selection)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 88.00},
        "skills_ratio": 1.0, "resp_sim": 0.88, "tools_sim": 0.86,
        "experience_matching": {
            "duration_factor": 1.000,
            "relevant_duration_years": 4.5,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.880,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Senior Applied NLP Engineer",
                    "company": "Lexicon Intelligence (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 2.5,
                    "semantic_similarity": 0.96,
                    "calibrated_similarity": 0.88,
                    "relevant_work_summary": "Optimized transformer inference pipelines and sequence tagging.",
                    "start_date": "2021-07-01",
                    "end_date": "2024-01-01",
                },
                {
                    "experience_index": 1,
                    "role": "Data Scientist",
                    "company": "TextWorks Inc (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 2.0,
                    "semantic_similarity": 0.90,
                    "calibrated_similarity": 0.72,
                    "relevant_work_summary": "Engineered n-gram topic models and text embeddings.",
                    "start_date": "2019-07-01",
                    "end_date": "2021-07-01",
                },
            ],
        },
    },
    "CAND-13": {
        "name": "Zoe Patel (Synthetic)",
        "target_jd": "JD-Pilot-02",
        "archetype": "NLP Engineer with Missing Dates",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 0.00},
        "skills_ratio": 1.0, "resp_sim": 0.88, "tools_sim": 0.85,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 0.0,
            "diagnostic_status": "missing_dates",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.900,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "NLP Systems Architect",
                    "company": "DeepText Research (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 0.0,
                    "semantic_similarity": 0.96,
                    "calibrated_similarity": 0.90,
                    "relevant_work_summary": "Published transformer compression methods.",
                    "start_date": None,
                    "end_date": None,
                }
            ],
        },
    },
    "CAND-14": {
        "name": "David O'Connor (Synthetic)",
        "target_jd": "JD-Pilot-02",
        "archetype": "Overlapping Academic & Industry ML (Time-Sliced Deduplication)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 64.50},
        "skills_ratio": 1.0, "resp_sim": 0.86, "tools_sim": 0.85,
        "experience_matching": {
            "duration_factor": 0.750,
            "relevant_duration_years": 3.0,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.860,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Postdoctoral NLP Researcher",
                    "company": "Synthetic University AI Institute",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 3.0,
                    "semantic_similarity": 0.95,
                    "calibrated_similarity": 0.86,
                    "relevant_work_summary": "Researched multi-lingual attention mechanisms.",
                    "start_date": "2021-01-01",
                    "end_date": "2024-01-01",
                },
                {
                    "experience_index": 1,
                    "role": "Part-Time ML Consultant",
                    "company": "Syntactic Apps (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 2.5,
                    "semantic_similarity": 0.94,
                    "calibrated_similarity": 0.82,
                    "relevant_work_summary": "Deployed transformer search models.",
                    "start_date": "2021-06-01",
                    "end_date": "2023-12-01",
                },
            ],
        },
    },
    "CAND-15": {
        "name": "Brenda Scott (Synthetic)",
        "target_jd": "JD-Pilot-02",
        "archetype": "Traditional BI Analyst (Rule 10 Zero Score)",
        "human_ground_truth": {"grade": 0, "label": "Unqualified / Irrelevant", "r1": 0, "r2": 0},
        "expected_scores": {"legacy_exp": 0.00, "evidence_exp": 0.00},
        "skills_ratio": 0.25, "resp_sim": 0.55, "tools_sim": 0.50,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 0.0,
            "diagnostic_status": "no_relevant_experience",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.000,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Senior Tableau Reporting Analyst",
                    "company": "Metrics Group (Synthetic)",
                    "decision": "IRRELEVANT",
                    "relevant": False,
                    "matched_domains": [],
                    "relevance_ratio": 0.0,
                    "relevant_duration_years": 0.0,
                    "semantic_similarity": 0.0,
                    "calibrated_similarity": 0.0,
                    "relevant_work_summary": "Built dashboard views and SQL extracts.",
                    "start_date": "2018-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-16": {
        "name": "Dr. Elena Rostova (Twin Stability Test)",
        "target_jd": "JD-Pilot-02",
        "archetype": "Twin Profile to CAND-09 (Engine Determinism Check)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 100.0, "evidence_exp": 92.00},
        "skills_ratio": 1.0, "resp_sim": 0.92, "tools_sim": 0.92,
        "experience_matching": {
            "duration_factor": 1.000,
            "relevant_duration_years": 5.5,
            "diagnostic_status": "duration_calculated",
            "saturation_target_years": 4.0,
            "range_status": "min_only",
            "aggregated_similarity": 0.920,
            "minimum_years": 4.0,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Staff NLP Research Scientist",
                    "company": "Cognitive AI Labs (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Natural Language Processing"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 5.5,
                    "semantic_similarity": 0.97,
                    "calibrated_similarity": 0.92,
                    "relevant_work_summary": "Trained and deployed billion-parameter transformer foundation models.",
                    "start_date": "2018-07-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },

    # --------------------------------------------------------------------------
    # JD-Pilot-03 Cohort (G1-C Unbounded Range, Cloud Infra + Distributed Storage)
    # --------------------------------------------------------------------------
    "CAND-17": {
        "name": "Vikram Sethi (Synthetic)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Senior Infrastructure Architect (G1-C Safeguard Active)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 88.00, "evidence_exp": 0.00},
        "skills_ratio": 1.0, "resp_sim": 0.90, "tools_sim": 0.90,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 6.0,
            "diagnostic_status": "unspecified",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.880,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Principal Systems Architect",
                    "company": "Distributed Storage Systems (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Infrastructure", "Distributed Storage"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 6.0,
                    "semantic_similarity": 0.96,
                    "calibrated_similarity": 0.88,
                    "relevant_work_summary": "Engineered distributed Ceph storage clusters and multi-region K8s topologies.",
                    "start_date": "2018-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-18": {
        "name": "Hannah Abbott (Synthetic)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Cloud Systems Admin (G1-C Single Domain)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 42.00, "evidence_exp": 0.00},
        "skills_ratio": 0.75, "resp_sim": 0.82, "tools_sim": 0.80,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 4.0,
            "diagnostic_status": "unspecified",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.420,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Cloud Systems Administrator",
                    "company": "Scale Infra Corp (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Infrastructure"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 4.0,
                    "semantic_similarity": 0.94,
                    "calibrated_similarity": 0.84,
                    "relevant_work_summary": "Administered production Kubernetes clusters and Linux hosts.",
                    "start_date": "2020-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-19": {
        "name": "Carlos Gomez (Synthetic)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Multi-Role Linux & Storage Admin (G1-C Multi-Role)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 85.00, "evidence_exp": 0.00},
        "skills_ratio": 1.0, "resp_sim": 0.88, "tools_sim": 0.86,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 5.0,
            "diagnostic_status": "unspecified",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.850,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Kubernetes Administrator",
                    "company": "ClusterWorks (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Infrastructure"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 3.0,
                    "semantic_similarity": 0.96,
                    "calibrated_similarity": 0.88,
                    "relevant_work_summary": "Maintained multi-node Kubernetes deployments.",
                    "start_date": "2021-01-01",
                    "end_date": "2024-01-01",
                },
                {
                    "experience_index": 1,
                    "role": "Storage Operations Engineer",
                    "company": "DataStore LLC (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Distributed Storage"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 2.0,
                    "semantic_similarity": 0.94,
                    "calibrated_similarity": 0.82,
                    "relevant_work_summary": "Managed petabyte Ceph and MinIO clusters.",
                    "start_date": "2019-01-01",
                    "end_date": "2021-01-01",
                },
            ],
        },
    },
    "CAND-20": {
        "name": "Nadia Ivanova (Synthetic)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Junior DevOps Specialist (G1-C Marginal Alignment)",
        "human_ground_truth": {"grade": 1, "label": "Marginal Fit", "r1": 1, "r2": 1},
        "expected_scores": {"legacy_exp": 34.00, "evidence_exp": 0.00},
        "skills_ratio": 0.50, "resp_sim": 0.70, "tools_sim": 0.70,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 1.5,
            "diagnostic_status": "unspecified",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.340,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Junior DevOps Assistant",
                    "company": "CloudStarter (Synthetic)",
                    "decision": "AMBIGUOUS",
                    "relevant": True,
                    "matched_domains": ["Cloud Infrastructure"],
                    "relevance_ratio": 0.5,
                    "relevant_duration_years": 1.5,
                    "semantic_similarity": 0.89,
                    "calibrated_similarity": 0.68,
                    "relevant_work_summary": "Assisted with Docker and basic CI pipelines.",
                    "start_date": "2022-06-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-21": {
        "name": "Thomas Reed (Synthetic)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Missing Dates Infrastructure Dev (G1-C Dual Safeguard)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 80.00, "evidence_exp": 0.00},
        "skills_ratio": 1.0, "resp_sim": 0.86, "tools_sim": 0.85,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 0.0,
            "diagnostic_status": "unspecified",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.800,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Systems Infrastructure Engineer",
                    "company": "Networked Systems (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Infrastructure", "Distributed Storage"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 0.0,
                    "semantic_similarity": 0.93,
                    "calibrated_similarity": 0.80,
                    "relevant_work_summary": "Engineered distributed systems without employment dates.",
                    "start_date": None,
                    "end_date": None,
                }
            ],
        },
    },
    "CAND-22": {
        "name": "Fiona Gallagher (Synthetic)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Overlapping Contract Sysadmin (G1-C Overlapping)",
        "human_ground_truth": {"grade": 2, "label": "Good / Partial Fit", "r1": 2, "r2": 2},
        "expected_scores": {"legacy_exp": 75.00, "evidence_exp": 0.00},
        "skills_ratio": 0.75, "resp_sim": 0.80, "tools_sim": 0.80,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 2.0,
            "diagnostic_status": "unspecified",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.750,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Contract Linux Sysadmin",
                    "company": "Hosting Provider Alpha (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Infrastructure"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 2.0,
                    "semantic_similarity": 0.92,
                    "calibrated_similarity": 0.75,
                    "relevant_work_summary": "Configured bare-metal Linux servers.",
                    "start_date": "2022-01-01",
                    "end_date": "2024-01-01",
                },
                {
                    "experience_index": 1,
                    "role": "Part-Time Storage Tech",
                    "company": "Hosting Provider Beta (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Distributed Storage"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 1.5,
                    "semantic_similarity": 0.92,
                    "calibrated_similarity": 0.75,
                    "relevant_work_summary": "Installed disk arrays.",
                    "start_date": "2022-06-01",
                    "end_date": "2023-12-01",
                },
            ],
        },
    },
    "CAND-23": {
        "name": "Lucas Meyer (Synthetic)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Unrelated React Frontend Dev (Rule 10 Zero Score)",
        "human_ground_truth": {"grade": 0, "label": "Unqualified / Irrelevant", "r1": 0, "r2": 0},
        "expected_scores": {"legacy_exp": 0.00, "evidence_exp": 0.00},
        "skills_ratio": 0.0, "resp_sim": 0.50, "tools_sim": 0.50,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 0.0,
            "diagnostic_status": "no_relevant_experience",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.000,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "React UI Designer",
                    "company": "Frontend Studio (Synthetic)",
                    "decision": "IRRELEVANT",
                    "relevant": False,
                    "matched_domains": [],
                    "relevance_ratio": 0.0,
                    "relevant_duration_years": 0.0,
                    "semantic_similarity": 0.0,
                    "calibrated_similarity": 0.0,
                    "relevant_work_summary": "Built UI components in React and CSS.",
                    "start_date": "2019-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
    "CAND-24": {
        "name": "Vikram Sethi (Twin Stability Test)",
        "target_jd": "JD-Pilot-03",
        "archetype": "Twin Profile to CAND-17 (Engine Determinism Check)",
        "human_ground_truth": {"grade": 3, "label": "Exceptional Fit", "r1": 3, "r2": 3},
        "expected_scores": {"legacy_exp": 88.00, "evidence_exp": 0.00},
        "skills_ratio": 1.0, "resp_sim": 0.90, "tools_sim": 0.90,
        "experience_matching": {
            "duration_factor": 0.000,
            "relevant_duration_years": 6.0,
            "diagnostic_status": "unspecified",
            "saturation_target_years": None,
            "range_status": "unspecified",
            "aggregated_similarity": 0.880,
            "minimum_years": None,
            "maximum_years": None,
            "experiences": [
                {
                    "experience_index": 0,
                    "role": "Principal Systems Architect",
                    "company": "Distributed Storage Systems (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": ["Cloud Infrastructure", "Distributed Storage"],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": 6.0,
                    "semantic_similarity": 0.96,
                    "calibrated_similarity": 0.88,
                    "relevant_work_summary": "Engineered distributed Ceph storage clusters and multi-region K8s topologies.",
                    "start_date": "2018-01-01",
                    "end_date": "2024-01-01",
                }
            ],
        },
    },
}


# ==============================================================================
# 4. FACTORY & ACCESS HELPERS (PREVENT MUTATION)
# ==============================================================================

def get_candidate_match_result(candidate_id: str) -> dict[str, Any]:
    """
    Returns a fresh, unmutated copy of the candidate match result dictionary
    ready to be scored by RankingEngine.score_candidate().
    """
    if candidate_id not in SYNTHETIC_CANDIDATE_FIXTURES:
        raise KeyError(f"Candidate fixture '{candidate_id}' not found.")

    cand = deepcopy(SYNTHETIC_CANDIDATE_FIXTURES[candidate_id])
    jd_id = cand["target_jd"]

    exact_matching, semantic_retrieval = _make_standard_components_a_b_c(
        jd_id=jd_id,
        skills_ratio=cand["skills_ratio"],
        resp_sim=cand["resp_sim"],
        tools_sim=cand["tools_sim"],
    )

    return {
        "upload_id": f"upload_synthetic_{candidate_id.lower().replace('-', '_')}",
        "filename": f"{candidate_id.lower()}_synthetic.pdf",
        "jd_id": jd_id,
        "exact_matching": exact_matching,
        "semantic_retrieval": semantic_retrieval,
        "experience_matching": cand["experience_matching"],
    }


def get_candidate_meta(candidate_id: str) -> dict[str, Any]:
    """Returns metadata and ground truth for a candidate."""
    if candidate_id not in SYNTHETIC_CANDIDATE_FIXTURES:
        raise KeyError(f"Candidate fixture '{candidate_id}' not found.")
    fixture = SYNTHETIC_CANDIDATE_FIXTURES[candidate_id]
    return {
        "candidate_id": candidate_id,
        "name": fixture["name"],
        "target_jd": fixture["target_jd"],
        "archetype": fixture["archetype"],
        "human_ground_truth": deepcopy(fixture["human_ground_truth"]),
        "expected_scores": deepcopy(fixture["expected_scores"]),
    }


def get_jd_cohort_candidate_ids(jd_id: str) -> list[str]:
    """Returns candidate IDs belonging to a specific Job Description cohort."""
    return [
        cid for cid, c in SYNTHETIC_CANDIDATE_FIXTURES.items()
        if c["target_jd"] == jd_id
    ]
