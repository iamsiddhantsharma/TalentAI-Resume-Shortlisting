from app.services.embedding_service import embedding_service


text = "Natural Language Processing"

embedding = embedding_service.generate_embedding(text)

print("Text:")
print(text)

print("\nEmbedding dimension:")
print(len(embedding))

print("\nFirst 10 values:")
print(embedding[:10])
