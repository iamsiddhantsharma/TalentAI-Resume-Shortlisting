from app.services.evidence_service import evidence_service
from app.services.evidence_embedding_service import (
    evidence_embedding_service,
)
from app.schemas.job_description import JobDescriptionObject


job_description = JobDescriptionObject(
    required_skills=[
        "data mining and data cleansing techniques",
        "machine learning techniques",
        "applied statistics skills",
    ],
    responsibilities=[
        "Develop and optimize machine learning models for business problems",
        "Process, cleanse and verify data used for analysis",
        "Present analytical conclusions to stakeholders",
    ],
    experience_requirements=[
        {
            "minimum_years": 2,
            "maximum_years": 5,
            "preferred_domains": [
                "Retail",
                "Manufacturing",
            ],
        }
    ],
    tools_and_technologies=[
        "Python",
        "R",
        "Pandas",
        "Scikit-learn",
        "SQL",
        "AWS",
    ],
)


# ------------------------------------------------------
# STEP 1: Build JD evidence
# ------------------------------------------------------

evidence = evidence_service.build_jd_evidence(
    job_description
)


print("\nJD Evidence units:")
print(len(evidence))


# ------------------------------------------------------
# STEP 2: Generate embeddings
# ------------------------------------------------------

embedded_evidence = (
    evidence_embedding_service.embed_evidence(evidence)
)


print("\nEmbedded JD evidence:")
print(len(embedded_evidence))


# ------------------------------------------------------
# STEP 3: Inspect results
# ------------------------------------------------------

for item in embedded_evidence:

    print("\n----------------------------------------")

    print("Section:")
    print(item["section"])

    print("\nText:")
    print(item["text"])

    print("\nEmbedding dimension:")
    print(len(item["embedding"]))

    print("\nFirst 5 values:")
    print(item["embedding"][:5])
