import sys
from pathlib import Path
from datetime import date

backend_dir = Path(r"c:\Users\siddh\OneDrive\Desktop\Talent_AI\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ranking.ranking_service import ranking_engine
from app.services.experience_matching_service import experience_matching_service
from app.schemas.job_description_object import JobDescriptionObject, ExperienceRequirement
from app.schemas.resume_object import ResumeObject, Experience
from app.schemas.matching import CandidateExperienceItem

print("=== Simulating Diwakar Dehariya & Accenture JD Experience Evaluation ===")

# 1. ResumeObject for Diwakar Dehariya
diwakar_resume = ResumeObject(
    name="Diwakar Dehariya",
    email="diwakardehariya2110@gmail.com",
    skills=["Python", "Flask", "REST APIs", "Azure", "Cosmos DB", "Postman", "Swagger", "C++", "SQL"],
    experience=[
        Experience(
            company="Jigiriz Impex",
            role="Backend Developer Intern",
            start_date="06/2022",
            end_date="08/2022",
            description=(
                "Developed REST APIs using Python and Flask and implemented on Azure. "
                "Used the APIs to read and write from Cosmos DB. "
                "Tested these APIs in Postman and fixed bugs. "
                "Described the structure of these APIs and created documentation for the same using Swagger.io"
            )
        )
    ]
)

# 2. Date parsing test for JUN'22 - AUG'22
parsed_start, s_stat = experience_matching_service._parse_date_with_status("06/2022")
parsed_end, e_stat = experience_matching_service._parse_date_with_status("08/2022")
print(f"Start date: '06/2022' -> {parsed_start} ({s_stat})")
print(f"End date: '08/2022' -> {parsed_end} ({e_stat})")
if parsed_start and parsed_end:
    days = (parsed_end - parsed_start).days
    years = experience_matching_service.days_to_years(days)
    print(f"Duration: {days} days = {years:.2f} years")

# 3. Test with various JD ExperienceRequirement configurations
cases = [
    ("Single Domain: Computational Science", ["Computational Science"]),
    ("Single Domain: Python", ["Python"]),
    ("Single Domain: AI/ML", ["AI/ML"]),
    ("Multiple Domains: ['AI/ML', 'Cloud Technologies']", ["AI/ML", "Cloud Technologies"]),
    ("No preferred domains, only min_years=2", []),
]

for label, domains in cases:
    jd = JobDescriptionObject(
        required_skills=["Python", "Machine Learning", "NLP", "Deep Learning", "GenAI/LLMs"],
        responsibilities=["AI-solution development", "Testing", "Model development"],
        tools_and_technologies=["Azure", "Cosmos DB", "Postman", "Swagger"],
        experience_requirements=[
            ExperienceRequirement(
                minimum_years=2.0,
                maximum_years=5.0,
                preferred_domains=domains
            )
        ] if domains or "min_years" in label else []
    )

    criteria = ranking_engine.extract_jd_experience_criteria(jd)
    print(f"\n--- Scenario: {label} ---")
    print(f"Extracted JD Criteria (Denominator): {criteria} (count={len(criteria)})")

    # If Qwen classified the single internship as RELEVANT with matching domain
    if len(domains) == 1:
        relevance_decisions = [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "matched_domains": domains,
                "reason": "Used Python, REST APIs, and Azure which aligns with JD."
            }
        ]
    elif len(domains) > 1:
        # Suppose Qwen matched both or one domain
        relevance_decisions = [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "matched_domains": ["Cloud Technologies"] if "Cloud Technologies" in domains else domains,
                "reason": "Internship involved Azure cloud implementation."
            }
        ]
    else:
        relevance_decisions = [
            {
                "experience_index": 0,
                "decision": "RELEVANT",
                "matched_domains": [],
                "reason": "Relevant software development."
            }
        ]

    # Run deterministic experience matching
    exp_matching_result = experience_matching_service.match_experience(
        resume=diwakar_resume,
        job_description=jd,
        relevance_results=relevance_decisions
    )
    print(f"ExperienceMatchingService result:")
    print(f"  relevant_experience_found: {exp_matching_result.get('relevant_experience_found')}")
    print(f"  relevant_duration_years: {exp_matching_result.get('relevant_duration_years')}")
    print(f"  minimum_duration_satisfied: {exp_matching_result.get('minimum_duration_satisfied')}")
    print(f"  diagnostic_status: {exp_matching_result.get('diagnostic_status')}")

    # Run Component D scoring
    score, status, total, qual, evidence, notes = ranking_engine.calculate_experience_relevance_score(
        experience_matching_data=exp_matching_result,
        job_description=jd,
        relevance_decisions=relevance_decisions
    )
    print(f"Component D (calculate_experience_relevance_score):")
    print(f"  Score: {score}%")
    print(f"  Status: {status}")
    print(f"  Total criteria (denominator): {total}")
    print(f"  Qualifying criteria count: {qual}")
    print(f"  Evidence: {evidence}")
    print(f"  Notes: {notes}")
