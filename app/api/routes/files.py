import io
from uuid import UUID

import pikepdf
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.api.deps import DbSession
from app.models import RawRow, SourceFile, Transaction
from app.schemas.file import FileMetadata, FilePreviewResponse, FileUploadResponse
from app.services.storage import StorageService

router = APIRouter()
storage_service = StorageService()


def _unlock_pdf(content: bytes, password: str) -> bytes:
    """Remove password protection from a PDF in memory."""
    with pikepdf.open(io.BytesIO(content), password=password) as pdf:
        out = io.BytesIO()
        pdf.save(out)
        return out.getvalue()


@router.get("", response_model=list[FileMetadata])
def list_files(
    db: DbSession,
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort by uploaded_at: asc or desc"),
):
    """List all uploaded files with their metadata, sorted by upload date."""
    sort_col = SourceFile.uploaded_at.asc() if order == "asc" else SourceFile.uploaded_at.desc()
    files = db.query(SourceFile).order_by(sort_col).all()
    return [
        FileMetadata(
            file_id=f.id,
            filename=f.original_filename,
            account_id=f.account_id,
            account_name=f.account.account_name,
            status=f.parse_status,
            uploaded_at=f.uploaded_at,
            hash=f.file_hash,
        )
        for f in files
    ]


@router.get("/{file_id}/preview", response_model=FilePreviewResponse)
def preview_file(
    file_id: UUID,
    db: DbSession,
    limit: int = Query(20, ge=1, le=100, description="Number of rows to return"),
):
    """Return the first N raw rows of a processed file."""
    source_file = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not source_file:
        raise HTTPException(status_code=404, detail="File not found")

    rows = (
        db.query(RawRow)
        .filter(RawRow.source_file_id == file_id)
        .order_by(RawRow.row_index)
        .limit(limit)
        .all()
    )
    total_rows = db.query(RawRow).filter(RawRow.source_file_id == file_id).count()
    columns = list(rows[0].raw_data_json.keys()) if rows else []

    return FilePreviewResponse(
        file_id=source_file.id,
        filename=source_file.original_filename,
        columns=columns,
        rows=[r.raw_data_json for r in rows],
        total_rows=total_rows,
    )


@router.get("/{file_id}/url")
def get_file_url(
    file_id: UUID,
    db: DbSession,
    expires_in: int = Query(3600, ge=60, le=86400, description="URL validity in seconds"),
):
    """
    Return a short-lived signed URL to directly access the file in Supabase Storage.

    Not available for locally stored files (returns 501).
    """
    source_file = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not source_file:
        raise HTTPException(status_code=404, detail="File not found")

    url = storage_service.get_signed_url(source_file.storage_uri, expires_in)
    if url is None:
        raise HTTPException(
            status_code=501,
            detail="Signed URLs are only available when Supabase Storage is configured.",
        )

    return {"file_id": file_id, "url": url, "expires_in": expires_in}


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: UUID, db: DbSession):
    """
    Delete a source file from storage and the database.

    Returns 409 if the file has associated transactions — run
    DELETE /etl/reset/{file_id} first to remove them.
    """
    source_file = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not source_file:
        raise HTTPException(status_code=404, detail="File not found")

    tx_count = (
        db.query(Transaction).filter(Transaction.source_file_id == file_id).count()
    )
    if tx_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"File has {tx_count} associated transactions. "
                f"Use DELETE /etl/reset/{file_id} first."
            ),
        )

    storage_service.delete_file(source_file.storage_uri)
    db.delete(source_file)
    db.commit()


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
