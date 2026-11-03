from app.services.embedding_service import embedding_service


# ------------------------------------------------------
# TEST TEXTS
# ------------------------------------------------------

text_1 = (
    "Built a machine learning model to predict "
    "customer churn using Python and Scikit-learn."
)

text_2 = (
    "Develop and optimize machine learning models "
    "for business problems."
)

text_3 = (
    "Designed a restaurant website using HTML and CSS."
)


# ------------------------------------------------------
# GENERATE EMBEDDINGS
# ------------------------------------------------------

embedding_1 = embedding_service.generate_embedding(text_1)
embedding_2 = embedding_service.generate_embedding(text_2)
embedding_3 = embedding_service.generate_embedding(text_3)


# ------------------------------------------------------
# COSINE SIMILARITY
# ------------------------------------------------------

def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
) -> float:
    """
    Calculate cosine similarity between two vectors.
    """

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = sum(
        a * a
        for a in vector_a
    ) ** 0.5

    magnitude_b = sum(
        b * b
        for b in vector_b
    ) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (
        magnitude_a * magnitude_b
    )


# ------------------------------------------------------
# CALCULATE SIMILARITIES
# ------------------------------------------------------

similarity_related = cosine_similarity(
    embedding_1,
    embedding_2,
)

similarity_unrelated = cosine_similarity(
    embedding_1,
    embedding_3,
)


# ------------------------------------------------------
# DISPLAY RESULTS
# ------------------------------------------------------

print("\n========================================")
print("SEMANTIC SIMILARITY TEST")
print("========================================")

print("\nCandidate Evidence:")
print(text_1)

print("\nRelated JD Evidence:")
print(text_2)

print("\nUnrelated Candidate Evidence:")
print(text_3)

print("\n----------------------------------------")

print(
    f"\nSimilarity (related): "
    f"{similarity_related:.4f}"
)

print(
    f"Similarity (unrelated): "
    f"{similarity_unrelated:.4f}"
)

print("\n========================================")
