from pathlib import Path

from app.parser.parser_factory import parser_factory


TEST_FILES = [
    Path("sample.pdf"),
    Path("sample.docx"),
    Path("sample.txt"),
]


print("=" * 70)
print("TalentAI - Parser Factory Test")
print("=" * 70)


for file_path in TEST_FILES:

    print()
    print("-" * 70)
    print(f"Testing: {file_path}")
    print("-" * 70)

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        continue

    try:

        text = parser_factory.parse(
            str(file_path)
        )

        print("✅ Parser selected successfully")
        print(f"Characters extracted: {len(text)}")

        print("\nFirst 500 characters:")
        print("-" * 70)
        print(text[:500])

    except Exception as exc:

        print("❌ Parsing failed")
        print(f"Error: {exc}")


print()
print("=" * 70)
print("Parser factory test completed.")
print("=" * 70)
