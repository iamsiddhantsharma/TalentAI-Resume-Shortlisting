from app.services.text_normalizer import text_normalizer


def main():
    messy_text = """
        Python     Developer


    FastAPI        MongoDB


    Experience:    2     years


    Skills:
        Python
        C++
        Machine Learning


    Email:    candidate@example.com
    """

    print("\n========================================")
    print("PHASE 4 - TEXT NORMALIZER TEST")
    print("========================================")

    print("\n---------- BEFORE ----------")
    print(messy_text)

    normalized_text = text_normalizer.normalize(
        messy_text
    )

    print("\n---------- AFTER ----------")
    print(normalized_text)

    print("\n========================================")
    print("VALIDATION")
    print("========================================")

    assert normalized_text != ""

    assert "Python Developer" in normalized_text

    assert "FastAPI MongoDB" in normalized_text

    assert "Experience: 2 years" in normalized_text

    assert "Machine Learning" in normalized_text

    assert "candidate@example.com" in normalized_text

    # There should not be excessive blank lines.
    assert "\n\n\n" not in normalized_text

    # Text should not start or end with whitespace.
    assert normalized_text == normalized_text.strip()

    print("✓ Text is not empty")
    print("✓ Excessive spaces normalized")
    print("✓ Excessive blank lines removed")
    print("✓ Important technical information preserved")
    print("✓ Email preserved")
    print("✓ Leading/trailing whitespace removed")
    print("\nPHASE 4 NORMALIZER TEST PASSED")


if __name__ == "__main__":
    main()
