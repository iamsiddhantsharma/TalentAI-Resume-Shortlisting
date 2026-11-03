from pathlib import Path

import fitz

from app.parser.exceptions import ResumeTextExtractionError


class PDFParser:
    """
    Extracts text from PDF resumes using PyMuPDF.
    """

    def parse(self, file_path: str) -> str:
        path = Path(file_path)

        if not path.exists():
            raise ResumeTextExtractionError(
                f"PDF file does not exist: {file_path}"
            )

        try:
            with fitz.open(path) as document:
                pages = []

                for page in document:
                    text = page.get_text()

                    if text:
                        pages.append(text)

            extracted_text = "\n".join(pages).strip()

            if not extracted_text:
                raise ResumeTextExtractionError(
                    f"No text could be extracted from PDF: {file_path}"
                )

            return extracted_text

        except ResumeTextExtractionError:
            raise

        except Exception as exc:
            raise ResumeTextExtractionError(
                f"Failed to extract text from PDF: {file_path}"
            ) from exc


pdf_parser = PDFParser()
