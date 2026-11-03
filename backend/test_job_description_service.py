from pathlib import Path

from app.services.job_description_service import (
    job_description_service,
)


def test_pasted_text():
    text = """
    Backend Developer

    We are looking for a Python Backend Developer.

    Requirements:
    Python
    FastAPI
    MongoDB
    REST APIs

    Experience:
    0-2 years
    """

    result = job_description_service.process_text(
        text
    )

    print("\n==============================")
    print("PASTED JD TEST")
    print("==============================")
    print("JD ID:", result.jd_id)
    print("Input Type:", result.input_type)
    print("Status:", result.status)
    print("Text:")
    print(result.raw_text)

    assert result.status == "parsed"
    assert result.input_type == "text"
    assert result.raw_text


def test_file(
    file_path: str,
):
    path = Path(file_path)

    if not path.exists():
        print(
            f"\nSkipping missing file: {file_path}"
        )
        return

    result = job_description_service.process_file(
        file_path=str(path),
        filename=path.name,
    )

    print("\n==============================")
    print(f"FILE TEST: {path.name}")
    print("==============================")
    print("JD ID:", result.jd_id)
    print("Input Type:", result.input_type)
    print("Filename:", result.filename)
    print("Extension:", result.file_extension)
    print("Status:", result.status)
    print("Text:")
    print(result.raw_text[:1000])

    assert result.status == "parsed"
    assert result.input_type == "file"
    assert result.raw_text


if __name__ == "__main__":

    print(
        "\n"
        "========================================\n"
        "TalentAI - Phase 3 JD Parser Test\n"
        "========================================"
    )

    # ------------------------------------------
    # Test 1: Pasted JD
    # ------------------------------------------

    test_pasted_text()

    # ------------------------------------------
    # Test 2: PDF
    # ------------------------------------------

    test_file(
        "test_data/job_description.pdf"
    )

    # ------------------------------------------
    # Test 3: DOCX
    # ------------------------------------------

    test_file(
        "test_data/job_description.docx"
    )

    # ------------------------------------------
    # Test 4: TXT
    # ------------------------------------------

    test_file(
        "test_data/job_description.txt"
    )

    print(
        "\n========================================"
    )
    print(
        "ALL AVAILABLE JD TESTS PASSED"
    )
    print(
        "========================================"
    )
