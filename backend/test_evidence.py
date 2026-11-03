from app.services.evidence_service import evidence_service
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


evidence = evidence_service.build_resume_evidence(resume)


print("\nGenerated Resume Evidence:\n")

for item in evidence:
    print(f"[{item['section']}]")
    print(item["text"])
    print()
