import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def compute_transaction_fingerprint(
    source_file_id: UUID, row_index: int
) -> str:
    """
    Compute unique fingerprint for a transaction.
    Based on source_file_id + row_index to guarantee uniqueness per row per file.
    Re-uploading the same file is prevented at the file level via file_hash.
    """
    fingerprint_str = f"{source_file_id}|{row_index}"
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()
