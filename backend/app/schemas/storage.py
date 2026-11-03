from pydantic import BaseModel


class StoredFile(BaseModel):
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    sha256: str
    file_extension: str
