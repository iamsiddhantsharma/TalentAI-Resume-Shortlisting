from pathlib import Path

from app.parser.exceptions import ResumeTextExtractionError


class TXTParser:
    """
    Extracts text from TXT resumes.
    """

    def parse(self, file_path: str) -> str:
        path = Path(file_path)

        if not path.exists():
            raise ResumeTextExtractionError(
                f"TXT file does not exist: {file_path}"
            )

        try:
            extracted_text = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()

            if not extracted_text:
                raise ResumeTextExtractionError(
                    f"No text could be extracted from TXT: {file_path}"
                )

            return extracted_text

        except ResumeTextExtractionError:
            raise

        except Exception as exc:
            raise ResumeTextExtractionError(
                f"Failed to extract text from TXT: {file_path}"
            ) from exc


txt_parser = TXTParser()
