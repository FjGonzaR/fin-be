from uuid import UUID

from app.utils.hashing import compute_transaction_fingerprint


def compute_fingerprint(source_file_id: UUID, row_index: int) -> str:
    """Compute unique fingerprint for a transaction row."""
    return compute_transaction_fingerprint(source_file_id, row_index)
