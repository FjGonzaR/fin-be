import uuid
from pathlib import Path

from app.core.config import settings
from app.utils.hashing import compute_file_hash_bytes


class StorageService:
    def __init__(self):
        self._client = None
        if settings.supabase_url and settings.supabase_key:
            from supabase import create_client
            from storage3._sync.client import SyncStorageClient

            self._client = create_client(settings.supabase_url, settings.supabase_key)
            # Disable SSL verification (self-signed cert in local chain on macOS)
            self._client._storage = SyncStorageClient(
                url=str(self._client.storage_url),
                headers=self._client.options.headers,
                verify=False,
            )

    def _use_supabase(self) -> bool:
        return self._client is not None

    def save_file(self, file_content: bytes, original_filename: str) -> tuple[str, str]:
        """
        Upload file to Supabase Storage (or local fallback).

        Returns:
            tuple: (storage_uri, file_hash)
        """
        file_hash = compute_file_hash_bytes(file_content)
        file_extension = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        if self._use_supabase():
            prefix = settings.supabase_upload_prefix.rstrip("/")
            storage_path = f"{prefix}/{unique_filename}"
            self._client.storage.from_(settings.supabase_bucket).upload(
                storage_path,
                file_content,
                {"content-type": self._content_type(file_extension)},
            )
            return f"supabase://{settings.supabase_bucket}/{storage_path}", file_hash

        # Local fallback
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / unique_filename
        file_path.write_bytes(file_content)
        return str(file_path), file_hash

    def download_file(self, storage_uri: str) -> bytes:
        """Download file content from wherever it was stored."""
        if storage_uri.startswith("supabase://"):
            # supabase://<bucket>/<path>
            without_scheme = storage_uri[len("supabase://"):]
            bucket, _, storage_path = without_scheme.partition("/")
            return bytes(self._client.storage.from_(bucket).download(storage_path))

        return Path(storage_uri).read_bytes()

    @staticmethod
    def _content_type(ext: str) -> str:
        return {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pdf": "application/pdf",
        }.get(ext.lower(), "application/octet-stream")
