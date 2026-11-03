from app.services.evidence_service import evidence_service
from app.services.evidence_embedding_service import (
    evidence_embedding_service,
)
from app.schemas.resume_object import ResumeObject


resume = ResumeObject(
    name="Test Candidate",
    skills=[
        "Python",
        "Machine Learning",
        "SQL",
    ],
    projects=[
        {
            "name": "Customer Churn Prediction",
            "description": (
                "Built a machine learning model to predict "
                "customer churn."
            ),
            "technologies": [
                "Python",
                "Pandas",
                "Scikit-learn",
            ],
        }
    ],
    experience=[
        {
            "company": "ABC Analytics",
            "role": "Data Scientist",
            "description": (
                "Developed machine learning models "
                "for customer analytics."
            ),
        }
    ],
)


# ------------------------------------------------------
# BUILD EVIDENCE
# ------------------------------------------------------

evidence = evidence_service.build_resume_evidence(
    resume
)


print("\nEvidence units:")
print(len(evidence))


# ------------------------------------------------------
# GENERATE EMBEDDINGS
# ------------------------------------------------------

embedded_evidence = (
    evidence_embedding_service.embed_evidence(
        evidence
    )
)


print("\nEmbedded evidence:")
print(len(embedded_evidence))


# ------------------------------------------------------
# INSPECT RESULTS
# ------------------------------------------------------

for item in embedded_evidence:

    print("\n----------------------------------------")

    print("Source type:")
    print(item["source_type"])

    print("Section:")
    print(item["section"])

    print("Item index:")
    print(item["item_index"])

    print("\nText:")
    print(item["text"])

    print("\nEmbedding dimension:")
    print(len(item["embedding"]))

    print("\nFirst 5 values:")
    print(item["embedding"][:5])
