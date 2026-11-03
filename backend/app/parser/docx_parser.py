from pathlib import Path

from docx import Document

from app.parser.exceptions import ResumeTextExtractionError


class DOCXParser:
    """
    Extracts text from DOCX resumes using python-docx.
    """

    def parse(self, file_path: str) -> str:
        path = Path(file_path)

        if not path.exists():
            raise ResumeTextExtractionError(
                f"DOCX file does not exist: {file_path}"
            )

        try:
            document = Document(path)

            paragraphs = []

            for paragraph in document.paragraphs:
                text = paragraph.text.strip()

                if text:
                    paragraphs.append(text)

            extracted_text = "\n".join(paragraphs).strip()

            if not extracted_text:
                raise ResumeTextExtractionError(
                    f"No text could be extracted from DOCX: {file_path}"
                )

            return extracted_text

        except ResumeTextExtractionError:
            raise

        except Exception as exc:
            raise ResumeTextExtractionError(
                f"Failed to extract text from DOCX: {file_path}"
            ) from exc


docx_parser = DOCXParser()
