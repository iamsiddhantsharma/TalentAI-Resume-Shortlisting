from pathlib import Path

from app.config.settings import settings


class FileValidationService:

    def __init__(self):
        self.allowed_extensions = {
            ext.strip().lower()
            for ext in settings.ALLOWED_EXTENSIONS.split(",")
        }

    def is_supported(self, filename: str) -> bool:
        """
        Returns True if the file extension is supported.
        """

        extension = Path(filename).suffix.lower()

        return extension in self.allowed_extensions


validation_service = FileValidationService()
