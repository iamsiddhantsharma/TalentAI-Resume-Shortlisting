from app.preprocessing.text_normalizer import text_normalizer


raw_text = """
John Doe


Software Engineer


Python     FastAPI      MongoDB


Experience:\r\n
Software Engineer at ABC Company\t


"""


print("=" * 70)
print("TalentAI - Text Normalizer Test")
print("=" * 70)

print("\nRAW TEXT:")
print("-" * 70)
print(raw_text)

normalized_text = text_normalizer.normalize(raw_text)

print("\nNORMALIZED TEXT:")
print("-" * 70)
print(normalized_text)

print("\nCHARACTERS:")
print("-" * 70)
print(f"Before : {len(raw_text)}")
print(f"After  : {len(normalized_text)}")

print("\n" + "=" * 70)
print("Text normalization test completed.")
print("=" * 70)
