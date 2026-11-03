from pathlib import Path

from app.parser.docx_parser import DOCXParser
from app.parser.exceptions import ResumeTextExtractionError
from app.parser.pdf_parser import PDFParser
from app.parser.txt_parser import TXTParser


class ParserFactory:
    """
    Selects the appropriate resume parser based on
    the file extension.
    """

    def __init__(self) -> None:
        self._parsers = {
            ".pdf": PDFParser(),
            ".docx": DOCXParser(),
            ".txt": TXTParser(),
        }

    def get_parser(self, file_extension: str):
        """
        Return the parser corresponding to the file extension.
        """

        extension = file_extension.strip().lower()

        # Handle values such as:
        # PDF -> .pdf
        # DOCX -> .docx
        # TXT -> .txt
        if not extension.startswith("."):
            extension = f".{extension}"

        parser = self._parsers.get(extension)

        if parser is None:
            raise ResumeTextExtractionError(
                f"No parser available for file type: {extension}"
            )

        return parser

    def parse(
        self,
        file_path: str,
        file_extension: str | None = None,
    ) -> str:
        """
        Select the correct parser and extract text.

        If file_extension is supplied, it is used directly.
        Otherwise the extension is derived from file_path.
        """

        if file_extension:
            parser = self.get_parser(
                file_extension
            )
        else:
            extension = Path(
                file_path
            ).suffix.lower()

            parser = self.get_parser(
                extension
            )

        return parser.parse(file_path)


parser_factory = ParserFactory()
