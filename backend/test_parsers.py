from pathlib import Path

from app.parser.pdf_parser import PDFParser
from app.parser.docx_parser import DOCXParser
from app.parser.txt_parser import TXTParser


# --------------------------------------------------
# Test files
# --------------------------------------------------

TEST_FILES = {
    ".pdf": Path("sample.pdf"),
    ".docx": Path("sample.docx"),
    ".txt": Path("sample.txt"),
}


# --------------------------------------------------
# Parser instances
# --------------------------------------------------

parsers = {
    ".pdf": PDFParser(),
    ".docx": DOCXParser(),
    ".txt": TXTParser(),
}


# --------------------------------------------------
# Run parser tests
# --------------------------------------------------

print("=" * 70)
print("TalentAI - Resume Parser Test")
print("=" * 70)


for extension, file_path in TEST_FILES.items():

    print()
    print("-" * 70)
    print(f"Testing: {file_path}")
    print(f"Type: {extension}")
    print("-" * 70)

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        continue

    try:
        parser = parsers[extension]

        extracted_text = parser.parse(
            str(file_path)
        )

        print("✅ Parsing successful")
        print()
        print("Extracted text:")
        print("=" * 70)

        print(extracted_text[:2000])

        if len(extracted_text) > 2000:
            print()
            print("... [text truncated for display]")

        print()
        print(f"Characters extracted: {len(extracted_text)}")

    except Exception as exc:
        print("❌ Parsing failed")
        print(f"Error: {exc}")


print()
print("=" * 70)
print("Parser testing completed.")
print("=" * 70)
