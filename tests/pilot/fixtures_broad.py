"""
TalentAI — Stage 5E.3: Broad Synthetic Validation Cohort Fixtures

This module implements the broad synthetic evaluation fixtures specified in
Stage 5E.3.1 (tests/pilot/stage_5e3_1_broader_validation_plan.md):
- 12 synthetic Job Descriptions across 6 technical job families.
- 240 synthetic candidate profiles (exactly 20 candidates per JD cohort).
- Comprehensive coverage of Gate 1 experience range paradigms:
  * Case 1: Bounded Range (Y_min to Y_max, Y_target = Y_max)
  * Case 2: Minimum-Only Range (Y_min only, Y_target = Y_min)
  * Case 3: Maximum-Only Range (Y_max only, Y_target = Y_max)
  * Case 4: G1-C Unbounded Range (No duration specified, D=0.000)
- Explicit edge cases:
  * Proportional duration damping (D = 0.25, 0.50, 0.75)
  * Over-saturation tenure clamping (15+ years tenure, D = 1.000)
  * Missing employment dates (D = 0.000, diagnostic_status = 'missing_dates')
  * Inverted / malformed dates (D = 0.000, diagnostic_status = 'invalid_date_range')
  * Fragmented short-term contractor stints (multi-role duration summation)
  * Concurrent overlapping roles (time-sliced max(r_k) duration pooling)
  * Rule 10 irrelevant backgrounds (strict zeroing)
  * Deterministic stability twin pairs (identical scores and ranks)

Safety & Privacy Invariants:
- 100% fictional, synthetic names, companies, and work histories.
- Zero PII, zero production candidate data, zero real resumes.
- Pure in-memory data structures (zero database connections, zero external calls).
- Candidate profiles and ground-truth labels are stored in separate dictionaries
  to prevent benchmark circularity or model score leakage.
"""

from copy import deepcopy
from typing import Any

from app.schemas.job_description_object import (
    ExperienceRequirement,
    JobDescriptionObject,
)

# ==============================================================================
# 1. 12 SYNTHETIC JOB DESCRIPTIONS ACROSS 6 STRATA
# ==============================================================================

BROAD_JOB_DESCRIPTIONS: dict[str, JobDescriptionObject] = {
    # Stratum 1: Backend & Distributed Systems
    "JD-BROAD-01": JobDescriptionObject(
        required_skills=["Go", "Raft", "gRPC", "RocksDB", "PostgreSQL"],
        responsibilities=[
            "Architect fault-tolerant replicated storage topologies",
            "Optimize write-ahead logging and snapshotting performance",
            "Design multi-node consensus state machines",
        ],
        tools_and_technologies=["Docker", "Kubernetes", "Prometheus", "Grafana"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=4.0,
                maximum_years=8.0,
                preferred_domains=["Distributed Storage", "Consensus Systems"],
            )
        ],
    ),
    "JD-BROAD-02": JobDescriptionObject(
        required_skills=["Python", "FastAPI", "Kafka", "PostgreSQL", "Redis"],
        responsibilities=[
            "Build and maintain event-driven asynchronous microservices",
            "Implement high-throughput message publishing pipelines",
            "Design RESTful API schemas and OpenAPI contracts",
        ],
        tools_and_technologies=["Docker", "Kafka", "PostgreSQL", "GitHub Actions"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=None,
                maximum_years=4.0,
                preferred_domains=["REST APIs", "Event-Driven Architecture"],
            )
        ],
    ),

    # Stratum 2: Frontend, Mobile & Full-Stack
    "JD-BROAD-03": JobDescriptionObject(
        required_skills=["TypeScript", "React", "Next.js", "GraphQL", "TailwindCSS"],
        responsibilities=[
            "Architect enterprise server-side rendered web applications",
            "Optimize Core Web Vitals and client bundle performance",
            "Establish modular design system component architectures",
        ],
        tools_and_technologies=["Vite", "Webpack", "Cypress", "Storybook"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=5.0,
                maximum_years=None,
                preferred_domains=["Modern Web Platforms", "Frontend Performance Optimization"],
            )
        ],
    ),
    "JD-BROAD-04": JobDescriptionObject(
        required_skills=["Swift", "SwiftUI", "Combine", "CoreData", "XCTest"],
        responsibilities=[
            "Develop high-performance offline-first mobile applications",
            "Architect modern Swift async/await concurrent networking",
            "Profile memory footprint and rendering frame rates",
        ],
        tools_and_technologies=["Xcode", "TestFlight", "Fastlane", "GitLab CI"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=3.0,
                maximum_years=6.0,
                preferred_domains=["iOS Frameworks", "SwiftUI / Swift Concurrency"],
            )
        ],
    ),

    # Stratum 3: AI, Machine Learning & Data
    "JD-BROAD-05": JobDescriptionObject(
        required_skills=["Python", "PyTorch", "vLLM", "Triton", "Ray"],
        responsibilities=[
            "Deploy and scale low-latency LLM inference engines",
            "Implement automated model evaluation and alignment pipelines",
            "Architect distributed model caching and batching topologies",
        ],
        tools_and_technologies=["Kubernetes", "Ray", "Triton", "MLflow", "Docker"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=4.0,
                maximum_years=None,
                preferred_domains=["Model Serving", "LLMOps / Pipeline Orchestration"],
            )
        ],
    ),
    "JD-BROAD-06": JobDescriptionObject(
        required_skills=["Scala", "Spark", "Kafka", "Delta Lake", "SQL"],
        responsibilities=[
            "Engineer petabyte-scale streaming ingestion pipelines",
            "Optimize Delta Lake table partitioning and compaction",
            "Build reliable exactly-once event processing topologies",
        ],
        tools_and_technologies=["Spark", "Kafka", "Airflow", "Databricks", "Terraform"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=3.0,
                maximum_years=7.0,
                preferred_domains=["Apache Spark", "Real-Time Streaming Lakehouse"],
            )
        ],
    ),

    # Stratum 4: DevOps, SRE & Cloud Infrastructure
    "JD-BROAD-07": JobDescriptionObject(
        required_skills=["Go", "Linux", "Kubernetes", "Prometheus", "OpenTelemetry"],
        responsibilities=[
            "Architect high-availability multi-region telemetry systems",
            "Establish automated SLO monitoring and incident alerting",
            "Lead disaster recovery exercises and chaos engineering tests",
        ],
        tools_and_technologies=["Prometheus", "Grafana", "Kubernetes", "Datadog", "Terraform"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=4.0,
                maximum_years=7.0,
                preferred_domains=["Incident Management", "Cloud Observability & Telemetry"],
            )
        ],
    ),
    "JD-BROAD-08": JobDescriptionObject(
        required_skills=["Terraform", "AWS", "GCP", "Kubernetes", "Ansible"],
        responsibilities=[
            "Design resilient hybrid cloud network topologies",
            "Standardize modular infrastructure-as-code automation",
            "Establish multi-cloud security governance and cost guardrails",
        ],
        tools_and_technologies=["Terraform", "Ansible", "Kubernetes", "AWS CloudFormation", "Vault"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=None,
                maximum_years=None,
                preferred_domains=["Multi-Cloud Architecture", "Infrastructure as Code"],
            )
        ],
    ),

    # Stratum 5: Security & Systems Engineering
    "JD-BROAD-09": JobDescriptionObject(
        required_skills=["Python", "AWS IAM", "Kubernetes", "OIDC", "Trivy"],
        responsibilities=[
            "Architect least-privilege Zero Trust identity policies",
            "Integrate automated vulnerability scanning into CI/CD pipelines",
            "Lead cloud posture assessments and threat modeling reviews",
        ],
        tools_and_technologies=["Trivy", "Vault", "Falco", "GitHub Actions", "AWS GuardDuty"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=4.0,
                maximum_years=None,
                preferred_domains=["Zero Trust Architecture", "Cloud IAM & Governance", "DevSecOps"],
            )
        ],
    ),
    "JD-BROAD-10": JobDescriptionObject(
        required_skills=["C", "C++", "FreeRTOS", "ARM Cortex", "I2C/SPI"],
        responsibilities=[
            "Develop deterministic real-time embedded firmware",
            "Write board support packages and peripheral device drivers",
            "Perform hardware-in-the-loop debugging with oscilloscopes",
        ],
        tools_and_technologies=["GDB", "J-Link", "CMake", "FreeRTOS", "Saleae Logic"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=3.0,
                maximum_years=5.0,
                preferred_domains=["Real-Time Operating Systems (RTOS)"],
            )
        ],
    ),

    # Stratum 6: Quality & Engineering Leadership
    "JD-BROAD-11": JobDescriptionObject(
        required_skills=["Python", "Playwright", "Pytest", "Docker", "REST APIs"],
        responsibilities=[
            "Architect scalable end-to-end test automation suites",
            "Implement automated regression testing in continuous delivery pipelines",
            "Build API contract and load testing infrastructures",
        ],
        tools_and_technologies=["Playwright", "Pytest", "Docker", "Locust", "Postman"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=3.0,
                maximum_years=None,
                preferred_domains=["Automated Test Frameworks"],
            )
        ],
    ),
    "JD-BROAD-12": JobDescriptionObject(
        required_skills=["System Design", "Agile Leadership", "Go", "Kubernetes", "Microservices"],
        responsibilities=[
            "Lead cross-functional engineering teams delivering critical platforms",
            "Drive architectural roadmaps and high-level design specifications",
            "Mentor senior engineers and streamline development lifecycles",
        ],
        tools_and_technologies=["Jira", "GitHub", "Kubernetes", "Figma", "Confluence"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=None,
                maximum_years=None,
                preferred_domains=["Technical Delivery Leadership", "Distributed Systems Architecture"],
            )
        ],
    ),
}

# Mapping of JD Stratum metadata
JD_STRATA_METADATA: dict[str, dict[str, Any]] = {
    "JD-BROAD-01": {"family": "Backend & Distributed Systems", "paradigm": "Bounded", "target_years": 8.0, "m_domains": 2},
    "JD-BROAD-02": {"family": "Backend & Distributed Systems", "paradigm": "Max-Only", "target_years": 4.0, "m_domains": 2},
    "JD-BROAD-03": {"family": "Frontend, Mobile & Full-Stack", "paradigm": "Min-Only", "target_years": 5.0, "m_domains": 2},
    "JD-BROAD-04": {"family": "Frontend, Mobile & Full-Stack", "paradigm": "Bounded", "target_years": 6.0, "m_domains": 2},
    "JD-BROAD-05": {"family": "AI, Machine Learning & Data", "paradigm": "Min-Only", "target_years": 4.0, "m_domains": 2},
    "JD-BROAD-06": {"family": "AI, Machine Learning & Data", "paradigm": "Bounded", "target_years": 7.0, "m_domains": 2},
    "JD-BROAD-07": {"family": "DevOps, SRE & Cloud Infrastructure", "paradigm": "Bounded", "target_years": 7.0, "m_domains": 2},
    "JD-BROAD-08": {"family": "DevOps, SRE & Cloud Infrastructure", "paradigm": "Unbounded / G1-C", "target_years": None, "m_domains": 2},
    "JD-BROAD-09": {"family": "Security & Systems Engineering", "paradigm": "Min-Only", "target_years": 4.0, "m_domains": 3},
    "JD-BROAD-10": {"family": "Security & Systems Engineering", "paradigm": "Bounded", "target_years": 5.0, "m_domains": 1},
    "JD-BROAD-11": {"family": "Quality & Engineering Leadership", "paradigm": "Min-Only", "target_years": 3.0, "m_domains": 1},
    "JD-BROAD-12": {"family": "Quality & Engineering Leadership", "paradigm": "Unbounded / G1-C", "target_years": None, "m_domains": 2},
}


# ==============================================================================
# 2. STANDARDIZED NON-EXPERIENCE COMPONENT GENERATOR
# ==============================================================================

def _make_broad_components_a_b_c(
    jd_id: str,
    skills_ratio: float = 1.0,
    resp_sim: float = 0.85,
    tools_sim: float = 0.88,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generates standardized ExactMatching and SemanticRetrieval payloads for any JD."""
    jd = BROAD_JOB_DESCRIPTIONS[jd_id]
    skills = jd.required_skills
    resps = jd.responsibilities
    tools = jd.tools_and_technologies

    # Exact matching (Component A)
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

    # Semantic retrieval (Components B & C)
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
# 3. 240 SYNTHETIC CANDIDATE PROFILES & INDEPENDENT GROUND-TRUTH LABELS
# ==============================================================================

SYNTHETIC_BROAD_CANDIDATE_FIXTURES: dict[str, dict[str, Any]] = {}
BROAD_GROUND_TRUTH_LABELS: dict[str, dict[str, Any]] = {}

def _register_broad_candidate(
    cid: str,
    target_jd: str,
    name: str,
    archetype: str,
    grade: int,
    label: str,
    r1: int,
    r2: int,
    adjudicated: bool,
    edge_markers: list[str],
    skills_ratio: float,
    resp_sim: float,
    tools_sim: float,
    dur_factor: float,
    rel_years: float,
    diag_status: str,
    experiences: list[dict[str, Any]],
):
    """Registers a candidate fixture and its separated ground-truth label."""
    meta = JD_STRATA_METADATA[target_jd]
    jd = BROAD_JOB_DESCRIPTIONS[target_jd]
    req = jd.experience_requirements[0]

    # Explicit range_status determination per approved Gate 1 semantics
    if req.minimum_years is not None and req.maximum_years is not None:
        range_status = "bounded"
    elif req.minimum_years is not None and req.maximum_years is None:
        range_status = "min_only"
    elif req.minimum_years is None and req.maximum_years is not None:
        range_status = "max_only"
    else:
        range_status = "unspecified"
    
    # Store candidate inputs (zero model score fields)
    SYNTHETIC_BROAD_CANDIDATE_FIXTURES[cid] = {
        "candidate_id": cid,
        "name": f"{name} (Synthetic)",
        "target_jd": target_jd,
        "archetype": archetype,
        "edge_markers": edge_markers,
        "skills_ratio": skills_ratio,
        "resp_sim": resp_sim,
        "tools_sim": tools_sim,
        "experience_matching": {
            "duration_factor": dur_factor,
            "relevant_duration_years": rel_years,
            "diagnostic_status": diag_status,
            "saturation_target_years": meta["target_years"],
            "range_status": range_status,
            "minimum_years": req.minimum_years,
            "maximum_years": req.maximum_years,
            "experiences": experiences,
        },
    }

    # Store ground-truth label strictly separate from candidate profile
    BROAD_GROUND_TRUTH_LABELS[cid] = {
        "candidate_id": cid,
        "target_jd": target_jd,
        "grade": grade,
        "label": label,
        "r1": r1,
        "r2": r2,
        "adjudicated": adjudicated,
        "binary_relevance": 1 if grade >= 2 else 0,
    }


# Template data for 20 synthetic candidate archetypes applied across each JD cohort
_ARCHETYPE_TEMPLATES = [
    # (k, title_suffix, grade, label, r1, r2, adj, edge_markers, skills_r, resp_s, tools_s, dur_ratio, sim_m1, sim_m2)
    (1, "Lead Domain Expert (Tenure Saturation & High Dual-Domain)", 3, "Exceptional Fit", 3, 3, False, ["tenure_saturation"], 1.0, 0.90, 0.90, 1.25, 0.92, 0.88),
    (2, "Veteran Architect (Multi-Role High Relevance)", 3, "Exceptional Fit", 3, 3, False, ["multi_role_excellence"], 1.0, 0.88, 0.90, 1.10, 0.88, 0.85),
    (3, "Principal Specialist (High Primary Domain Depth)", 3, "Exceptional Fit", 3, 2, True, ["adjudicated_depth"], 1.0, 0.85, 0.88, 1.00, 0.86, 0.82),
    (4, "Single-Domain Specialist (Full Tenure, Missing Secondary Domain)", 2, "Good / Partial Fit", 2, 2, False, ["unsupported_domain_zero_fill"], 1.0, 0.85, 0.85, 1.00, 0.86, 0.00),
    (5, "Senior Engineer (Moderate Tenure Damping, Strong Skills)", 2, "Good / Partial Fit", 2, 2, False, ["proportional_damping_065"], 1.0, 0.85, 0.85, 0.65, 0.84, 0.80),
    (6, "Mid-Level Engineer (Moderate Tenure Damping, Solid Core)", 2, "Good / Partial Fit", 2, 2, False, ["proportional_damping_050"], 0.8, 0.80, 0.82, 0.50, 0.82, 0.78),
    (7, "Broad Generalist (Full Tenure, Moderate Similarity Across Domains)", 2, "Good / Partial Fit", 2, 2, False, ["moderate_similarity"], 0.8, 0.80, 0.80, 1.00, 0.68, 0.65),
    (8, "Junior Practitioner (Sub-threshold Tenure, Adjacent Experience)", 1, "Marginal Fit", 1, 1, False, ["adjacent_domain_low_tenure"], 0.6, 0.70, 0.70, 0.25, 0.55, 0.50),
    (9, "Experienced Misaligned Engineer (High Tenure, Peripheral Tech)", 1, "Marginal Fit", 1, 1, False, ["peripheral_experience"], 0.6, 0.65, 0.65, 1.00, 0.30, 0.20),
    (10, "Non-Technical Irrelevant Background (Rule 10 Strict Zeroing)", 0, "Unqualified / Irrelevant", 0, 0, False, ["rule10_irrelevant"], 0.0, 0.40, 0.40, 0.00, 0.00, 0.00),
    (11, "Early Career High Aptitude (Exact 25% Tenure Damping)", 2, "Good / Partial Fit", 2, 2, False, ["exact_damping_025"], 1.0, 0.88, 0.88, 0.25, 0.88, 0.85),
    (12, "Mid-Level Rising Dev (Exact 75% Tenure Damping)", 2, "Good / Partial Fit", 2, 2, False, ["exact_damping_075"], 1.0, 0.85, 0.88, 0.75, 0.85, 0.82),
    (13, "Distinguished Fellow (Long-Tenure Over-Saturation Clamping)", 3, "Exceptional Fit", 3, 3, False, ["tenure_clamping_15y"], 1.0, 0.92, 0.92, 2.50, 0.94, 0.90),
    (14, "Concurrent Overlapping Roles (Approved Time-Sliced Max Rule)", 2, "Good / Partial Fit", 2, 2, False, ["overlapping_concurrent"], 1.0, 0.85, 0.85, 0.70, 0.84, 0.80),
    (15, "Contractor Specialist (Fragmented Non-Overlapping Stints)", 2, "Good / Partial Fit", 2, 2, False, ["fragmented_tenure"], 1.0, 0.85, 0.85, 1.00, 0.82, 0.80),
    (16, "Qualified Engineer with Unverified Dates (Missing Dates Safeguard)", 2, "Good / Partial Fit", 2, 2, False, ["missing_dates"], 1.0, 0.88, 0.88, 0.00, 0.88, 0.85),
    (17, "Profile with Inverted Date Range (Invalid Date Safeguard)", 1, "Marginal Fit", 1, 1, False, ["invalid_date_range"], 0.8, 0.75, 0.75, 0.00, 0.75, 0.70),
    (18, "Unbounded Paradigm Profile (G1-C Range Status Safeguard)", 3, "Exceptional Fit", 3, 3, False, ["unbounded_g1c"], 1.0, 0.90, 0.90, 0.00, 0.89, 0.88),
    (19, "Deterministic Stability Twin Alpha (Reproducibility Anchor)", 3, "Exceptional Fit", 3, 3, False, ["twin_stability_pair"], 1.0, 0.90, 0.90, 1.00, 0.90, 0.88),
    (20, "Deterministic Stability Twin Beta (Identical Duplicate to Alpha)", 3, "Exceptional Fit", 3, 3, False, ["twin_stability_pair"], 1.0, 0.90, 0.90, 1.00, 0.90, 0.88),
]

# Generate all 240 synthetic candidates across 12 JDs
_NAMES = [
    "Jordan Lee", "Casey Rivera", "Alex Mercer", "Riley Vance", "Taylor Morgan",
    "Samira Khan", "Devon Hayes", "Morgan Bailey", "Liam Chen", "Dr. Elena Rostova",
    "Avery Brooks", "Marcus Brody", "Zoe Patel", "David O'Connor", "Brenda Scott",
    "Vikram Sethi", "Hannah Abbott", "Carlos Gomez", "Nadia Ivanova", "Thomas Reed",
    "Fiona Gallagher", "Lucas Meyer", "Priya Nair", "Gabriel Silva"
]

_COMPANIES = [
    "Apex Systems (Synthetic)", "NovaCore Labs (Synthetic)", "Pinnacle Tech (Synthetic)",
    "Vanguard Platforms (Synthetic)", "Quantum Dynamics (Synthetic)", "Meridian Data (Synthetic)",
    "Horizon Cloud (Synthetic)", "Aether Networks (Synthetic)", "Strata Security (Synthetic)",
    "Prism Embedded (Synthetic)", "OmniQA Systems (Synthetic)", "Hyperion Solutions (Synthetic)"
]

for jd_idx in range(1, 13):
    jd_id = f"JD-BROAD-{jd_idx:02d}"
    meta = JD_STRATA_METADATA[jd_id]
    target_y = meta["target_years"] or 5.0
    domains = BROAD_JOB_DESCRIPTIONS[jd_id].experience_requirements[0].preferred_domains
    is_unbounded = meta["paradigm"] == "Unbounded / G1-C"

    for t in _ARCHETYPE_TEMPLATES:
        k = t[0]
        cid = f"BCAND-{(jd_idx - 1) * 20 + k:03d}"
        suffix = t[1]
        grade = t[2]
        label = t[3]
        r1 = t[4]
        r2 = t[5]
        adj = t[6]
        edge_markers = list(t[7])
        skills_r = t[8]
        resp_s = t[9]
        tools_s = t[10]
        dur_ratio = t[11]
        sim1 = t[12]
        sim2 = t[13]

        name = f"{_NAMES[(jd_idx * 7 + k) % len(_NAMES)]}_{k}"
        company = _COMPANIES[jd_idx - 1]

        # Calculate durations and candidate #18 paradigm-specific resolution
        if k == 18:
            if is_unbounded:
                suffix = "Unbounded Paradigm Profile (G1-C Range Status Safeguard)"
                grade = 3
                label = "Exceptional Fit"
                r1 = 3
                r2 = 3
                adj = False
                edge_markers = ["unbounded_g1c"]
                dur_factor = 0.000
                rel_years = 6.0
                diag_status = "unspecified"
            else:
                suffix = "Sub-threshold Tenure Candidate (Zero Qualifying Duration Safeguard)"
                grade = 1
                label = "Marginal Fit"
                r1 = 1
                r2 = 1
                adj = False
                edge_markers = ["subthreshold_tenure_zero_duration"]
                dur_factor = 0.000
                rel_years = 0.0
                diag_status = "duration_calculated"
        elif is_unbounded:
            dur_factor = 0.000
            rel_years = target_y * (1.0 if dur_ratio > 0 else 0.0)
            diag_status = "unspecified"
        elif "missing_dates" in edge_markers:
            dur_factor = 0.000
            rel_years = 0.0
            diag_status = "missing_dates"
        elif "invalid_date_range" in edge_markers:
            dur_factor = 0.000
            rel_years = 0.0
            diag_status = "invalid_date_range"
        elif "rule10_irrelevant" in edge_markers:
            dur_factor = 0.000
            rel_years = 0.0
            diag_status = "no_relevant_experience"
        else:
            rel_years = round(dur_ratio * target_y, 2)
            dur_factor = min(1.0, dur_ratio)
            diag_status = "duration_calculated"

        # Construct experiences list
        if "rule10_irrelevant" in edge_markers:
            exps = [{
                "experience_index": 0,
                "role": "Customer Service Representative",
                "company": "Retail Retailer (Synthetic)",
                "decision": "IRRELEVANT",
                "relevant": False,
                "matched_domains": [],
                "relevance_ratio": 0.0,
                "relevant_duration_years": 0.0,
                "semantic_similarity": 0.20,
                "calibrated_similarity": 0.00,
                "relevant_work_summary": "Handled customer phone inquiries and store merchandise stocking.",
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
            }]
        elif "missing_dates" in edge_markers:
            exps = [{
                "experience_index": 0,
                "role": f"Senior {domains[0]} Engineer",
                "company": company,
                "decision": "RELEVANT",
                "relevant": True,
                "matched_domains": list(domains),
                "relevance_ratio": 1.0,
                "relevant_duration_years": 0.0,
                "semantic_similarity": 0.95,
                "calibrated_similarity": sim1,
                "relevant_work_summary": f"Architected production infrastructure for {domains[0]}.",
                "start_date": None,
                "end_date": None,
            }]
        elif "invalid_date_range" in edge_markers:
            exps = [{
                "experience_index": 0,
                "role": f"{domains[0]} Developer",
                "company": company,
                "decision": "RELEVANT",
                "relevant": True,
                "matched_domains": [domains[0]],
                "relevance_ratio": 1.0,
                "relevant_duration_years": 0.0,
                "semantic_similarity": 0.85,
                "calibrated_similarity": sim1,
                "relevant_work_summary": f"Built platform software for {domains[0]}.",
                "start_date": "2024-01-01",
                "end_date": "2020-01-01",  # Inverted dates!
            }]
        elif "subthreshold_tenure_zero_duration" in edge_markers:
            # Candidate #18 in non-unbounded JDs: zero qualifying duration in target domains
            exps = [{
                "experience_index": 0,
                "role": f"Associate {domains[0]} Developer",
                "company": company,
                "decision": "RELEVANT",
                "relevant": True,
                "matched_domains": [domains[0]],
                "relevance_ratio": 1.0,
                "relevant_duration_years": 0.0,
                "semantic_similarity": 0.85,
                "calibrated_similarity": sim1,
                "relevant_work_summary": f"Recent contributor to {domains[0]}; domain tenure is sub-threshold.",
                "start_date": "2024-01-01",
                "end_date": "2024-01-01",
            }]
        elif "fragmented_tenure" in edge_markers:
            # 4 short-term stints
            stint_years = round(rel_years / 4.0, 2)
            exps = [
                {
                    "experience_index": i,
                    "role": f"Contract {domains[0]} Consultant {i+1}",
                    "company": f"Consulting Stint {i+1} (Synthetic)",
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": [domains[0]],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": stint_years,
                    "semantic_similarity": 0.90,
                    "calibrated_similarity": sim1,
                    "relevant_work_summary": f"Delivered contract milestones for {domains[0]}.",
                    "start_date": f"{2018 + i}-01-01",
                    "end_date": f"{2018 + i}-09-01",
                }
                for i in range(4)
            ]
        elif "overlapping_concurrent" in edge_markers:
            # Two concurrent overlapping roles (full-time + part-time)
            exps = [
                {
                    "experience_index": 0,
                    "role": f"Primary {domains[0]} Lead",
                    "company": company,
                    "decision": "RELEVANT",
                    "relevant": True,
                    "matched_domains": [domains[0]],
                    "relevance_ratio": 1.0,
                    "relevant_duration_years": rel_years,
                    "semantic_similarity": 0.92,
                    "calibrated_similarity": sim1,
                    "relevant_work_summary": f"Core engineering responsibilities for {domains[0]}.",
                    "start_date": "2021-01-01",
                    "end_date": "2024-01-01",
                },
                {
                    "experience_index": 1,
                    "role": f"Advisory {domains[-1]} Specialist",
                    "company": "Advisory Ventures (Synthetic)",
                    "decision": "AMBIGUOUS",
                    "relevant": True,
                    "matched_domains": [domains[-1]],
                    "relevance_ratio": 0.5,
                    "relevant_duration_years": round(rel_years * 0.6, 2),
                    "semantic_similarity": 0.85,
                    "calibrated_similarity": sim2,
                    "relevant_work_summary": f"Part-time advisory consulting for {domains[-1]}.",
                    "start_date": "2022-01-01",
                    "end_date": "2024-01-01",
                },
            ]
        elif len(domains) > 1 and sim2 > 0:
            # Dual domain candidate
            exps = [{
                "experience_index": 0,
                "role": f"Principal {domains[0]} & {domains[-1]} Specialist",
                "company": company,
                "decision": "RELEVANT",
                "relevant": True,
                "matched_domains": [domains[0], domains[-1]],
                "relevance_ratio": 1.0,
                "relevant_duration_years": rel_years,
                "semantic_similarity": 0.94,
                "calibrated_similarity": sim1,
                "relevant_work_summary": f"Engineered scalable systems spanning {domains[0]} and {domains[-1]}.",
                "start_date": "2018-01-01",
                "end_date": "2024-01-01",
            }]
        else:
            # Single domain candidate
            exps = [{
                "experience_index": 0,
                "role": f"Staff {domains[0]} Engineer",
                "company": company,
                "decision": "RELEVANT",
                "relevant": True,
                "matched_domains": [domains[0]],
                "relevance_ratio": 1.0,
                "relevant_duration_years": rel_years,
                "semantic_similarity": 0.90,
                "calibrated_similarity": sim1,
                "relevant_work_summary": f"Specialized in core {domains[0]} architecture and delivery.",
                "start_date": "2018-01-01",
                "end_date": "2024-01-01",
            }]

        _register_broad_candidate(
            cid=cid,
            target_jd=jd_id,
            name=name,
            archetype=f"{domains[0]} — {suffix}",
            grade=grade,
            label=label,
            r1=r1,
            r2=r2,
            adjudicated=adj,
            edge_markers=edge_markers,
            skills_ratio=skills_r,
            resp_sim=resp_s,
            tools_sim=tools_s,
            dur_factor=dur_factor,
            rel_years=rel_years,
            diag_status=diag_status,
            experiences=exps,
        )


# ==============================================================================
# 4. PUBLIC ACCESSOR FUNCTIONS
# ==============================================================================

def get_broad_candidate_match_result(candidate_id: str) -> dict[str, Any]:
    """
    Returns complete, isolated candidate match result dictionary ready for
    RankingEngine.score_candidate(match_result, jd).
    """
    if candidate_id not in SYNTHETIC_BROAD_CANDIDATE_FIXTURES:
        raise KeyError(f"Candidate '{candidate_id}' not found in broad synthetic fixtures.")

    cand = deepcopy(SYNTHETIC_BROAD_CANDIDATE_FIXTURES[candidate_id])
    jd_id = cand["target_jd"]

    exact_matching, semantic_retrieval = _make_broad_components_a_b_c(
        jd_id=jd_id,
        skills_ratio=cand["skills_ratio"],
        resp_sim=cand["resp_sim"],
        tools_sim=cand["tools_sim"],
    )

    return {
        "upload_id": f"upload_broad_{candidate_id.lower().replace('-', '_')}",
        "filename": f"{candidate_id.lower()}_synthetic.pdf",
        "jd_id": jd_id,
        "exact_matching": exact_matching,
        "semantic_retrieval": semantic_retrieval,
        "experience_matching": cand["experience_matching"],
    }


def get_broad_candidate_ground_truth(candidate_id: str) -> dict[str, Any]:
    """Returns independent human ground-truth relevance label."""
    if candidate_id not in BROAD_GROUND_TRUTH_LABELS:
        raise KeyError(f"Ground truth for candidate '{candidate_id}' not found.")
    return deepcopy(BROAD_GROUND_TRUTH_LABELS[candidate_id])


def get_broad_candidate_meta(candidate_id: str) -> dict[str, Any]:
    """Returns candidate profile metadata (name, archetype, edge markers, target JD)."""
    if candidate_id not in SYNTHETIC_BROAD_CANDIDATE_FIXTURES:
        raise KeyError(f"Candidate '{candidate_id}' not found in broad synthetic fixtures.")
    c = SYNTHETIC_BROAD_CANDIDATE_FIXTURES[candidate_id]
    return {
        "candidate_id": candidate_id,
        "name": c["name"],
        "target_jd": c["target_jd"],
        "archetype": c["archetype"],
        "edge_markers": list(c["edge_markers"]),
    }


def get_broad_jd_cohort_candidate_ids(jd_id: str) -> list[str]:
    """Returns list of all candidate IDs belonging to a specific JD cohort (exactly 20)."""
    return [
        cid for cid, c in SYNTHETIC_BROAD_CANDIDATE_FIXTURES.items()
        if c["target_jd"] == jd_id
    ]


# ==============================================================================
# 5. LIGHTWEIGHT IN-MEMORY FIXTURE INTEGRITY VERIFICATION
# ==============================================================================

def verify_broad_fixtures_integrity() -> dict[str, Any]:
    """
    Lightweight self-check validating structural integrity and invariants
    of the broad synthetic validation dataset without modifying external state.
    """
    jd_count = len(BROAD_JOB_DESCRIPTIONS)
    cand_count = len(SYNTHETIC_BROAD_CANDIDATE_FIXTURES)
    gt_count = len(BROAD_GROUND_TRUTH_LABELS)

    errors: list[str] = []

    # 1. Total counts
    if jd_count != 12:
        errors.append(f"Expected 12 Job Descriptions, found {jd_count}.")
    if cand_count != 240:
        errors.append(f"Expected 240 synthetic candidates, found {cand_count}.")
    if gt_count != 240:
        errors.append(f"Expected 240 ground-truth labels, found {gt_count}.")

    # 2. All four experience paradigms represented
    paradigms = {meta["paradigm"] for meta in JD_STRATA_METADATA.values()}
    required_paradigms = {"Bounded", "Min-Only", "Max-Only", "Unbounded / G1-C"}
    missing_paradigms = required_paradigms - paradigms
    if missing_paradigms:
        errors.append(f"Missing required experience paradigms: {missing_paradigms}.")

    # 3. Forbidden score leakage keys in candidate fixtures
    forbidden_keys = {
        "final_score", "expected_scores", "expected_score",
        "rank", "expected_rank", "score", "legacy_score", "legacy_exp", "evidence_exp"
    }

    # 4. Check candidate-to-JD pairing, range_status, and ground truth
    grade_counter = {0: 0, 1: 0, 2: 0, 3: 0}
    for jd_id, jd in BROAD_JOB_DESCRIPTIONS.items():
        cids = get_broad_jd_cohort_candidate_ids(jd_id)
        if len(cids) != 20:
            errors.append(f"{jd_id} has {len(cids)} candidates, expected exactly 20.")

        req = jd.experience_requirements[0]
        if req.minimum_years is not None and req.maximum_years is not None:
            expected_range_status = "bounded"
        elif req.minimum_years is not None and req.maximum_years is None:
            expected_range_status = "min_only"
        elif req.minimum_years is None and req.maximum_years is not None:
            expected_range_status = "max_only"
        else:
            expected_range_status = "unspecified"

        cohort_grades = {0: 0, 1: 0, 2: 0, 3: 0}

        for cid in cids:
            cand = SYNTHETIC_BROAD_CANDIDATE_FIXTURES[cid]
            # Check score leakage
            leaked = forbidden_keys.intersection(cand.keys())
            if leaked:
                errors.append(f"Candidate {cid} contains leaked score fields: {leaked}.")

            # Check range_status
            cand_rs = cand.get("experience_matching", {}).get("range_status")
            if cand_rs != expected_range_status:
                errors.append(
                    f"Candidate {cid} under {jd_id} has range_status '{cand_rs}', "
                    f"expected '{expected_range_status}'."
                )

            if cid not in BROAD_GROUND_TRUTH_LABELS:
                errors.append(f"Candidate {cid} lacks ground-truth label.")
            else:
                gt = BROAD_GROUND_TRUTH_LABELS[cid]
                # Check ground-truth independence
                gt_leaked = forbidden_keys.intersection(gt.keys())
                if gt_leaked:
                    errors.append(f"Ground truth for {cid} contains leaked fields: {gt_leaked}.")

                g = gt.get("grade")
                if g not in (0, 1, 2, 3):
                    errors.append(f"Candidate {cid} has invalid ground-truth grade: {g}.")
                else:
                    grade_counter[g] += 1
                    cohort_grades[g] += 1

                # Check binary relevance alignment
                expected_bin = 1 if g >= 2 else 0
                if gt.get("binary_relevance") != expected_bin:
                    errors.append(
                        f"Candidate {cid} has binary_relevance {gt.get('binary_relevance')}, "
                        f"expected {expected_bin} for grade {g}."
                    )

        # Check per-cohort distribution
        is_unbounded = (expected_range_status == "unspecified")
        if is_unbounded:
            if cohort_grades != {3: 7, 2: 9, 1: 3, 0: 1}:
                errors.append(
                    f"Unbounded cohort {jd_id} grade distribution {cohort_grades} "
                    f"does not match expected {{3: 7, 2: 9, 1: 3, 0: 1}}."
                )
        else:
            if cohort_grades != {3: 6, 2: 9, 1: 4, 0: 1}:
                errors.append(
                    f"Cohort {jd_id} grade distribution {cohort_grades} "
                    f"does not match expected {{3: 6, 2: 9, 1: 4, 0: 1}}."
                )

    # 5. Check overall ground-truth counts
    expected_total_grades = {3: 74, 2: 108, 1: 46, 0: 12}
    if grade_counter != expected_total_grades:
        errors.append(
            f"Overall grade distribution {grade_counter} does not match expected {expected_total_grades}."
        )

    return {
        "status": "PASS" if not errors else "FAIL",
        "job_descriptions_count": jd_count,
        "candidates_count": cand_count,
        "ground_truth_labels_count": gt_count,
        "grade_distribution": grade_counter,
        "relevant_candidates_count": grade_counter[3] + grade_counter[2],
        "non_relevant_candidates_count": grade_counter[1] + grade_counter[0],
        "paradigms_represented": sorted(list(paradigms)),
        "errors": errors,
    }
