import uuid
from pathlib import Path

from app.core.config import settings
from app.utils.hashing import compute_file_hash


class StorageService:
    def __init__(self, upload_dir: str = settings.upload_dir):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_content: bytes, original_filename: str) -> tuple[str, str]:
        """
        Save uploaded file to local storage.

        Returns:
            tuple: (storage_uri, file_hash)
        """
        # Generate unique filename
        file_extension = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = self.upload_dir / unique_filename

        # Write file
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Compute hash
        file_hash = compute_file_hash(file_path)

        # Return relative path as storage_uri
        storage_uri = str(file_path)

        return storage_uri, file_hash

    def get_file_path(self, storage_uri: str) -> Path:
        """Get Path object from storage_uri."""
        return Path(storage_uri)
