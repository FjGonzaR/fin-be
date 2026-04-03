import io
from uuid import UUID

import pikepdf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import DbSession
from app.models import SourceFile
from app.schemas.file import FileUploadResponse
from app.services.storage import StorageService

router = APIRouter()
storage_service = StorageService()


def _unlock_pdf(content: bytes, password: str) -> bytes:
    """Remove password protection from a PDF in memory."""
    with pikepdf.open(io.BytesIO(content), password=password) as pdf:
        out = io.BytesIO()
        pdf.save(out)
        return out.getvalue()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    db: DbSession,
    file: UploadFile = File(...),
    account_id: UUID = Form(...),
    file_password: str | None = Form(None, description="Password for password-protected files (e.g. Nequi PDF). Used to unlock the file before storage — not persisted."),
):
    """
    Upload a file for ETL processing.

    Returns source_file record.
    """
    # Validate file type
    _ALLOWED_EXTENSIONS = {".xlsx", ".pdf"}
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .xlsx and .pdf files are supported")

    file_type = ext.lstrip(".")

    # Read file content
    content = await file.read()

    # If a password was provided, unlock the PDF now so the plain file is stored
    if file_password and ext == ".pdf":
        try:
            content = _unlock_pdf(content, file_password)
        except pikepdf.PasswordError:
            raise HTTPException(status_code=400, detail="Invalid file password")

    # Save file and compute hash
    storage_uri, file_hash = storage_service.save_file(content, filename)

    # Check if file already exists by hash
    existing_file = (
        db.query(SourceFile).filter(SourceFile.file_hash == file_hash).first()
    )
    if existing_file:
        db.commit()
        return FileUploadResponse.model_validate(existing_file)

    # Create new source file record
    source_file = SourceFile(
        account_id=account_id,
        file_type=file_type,
        file_hash=file_hash,
        original_filename=file.filename,
        storage_uri=storage_uri,
        parse_status="UPLOADED",
    )
    db.add(source_file)
    db.commit()
    db.refresh(source_file)

    return FileUploadResponse.model_validate(source_file)
