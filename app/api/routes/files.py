from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import DbSession
from app.models import Account, SourceFile
from app.schemas.file import FileUploadResponse
from app.services.storage import StorageService
from app.utils.encryption import encrypt_password

router = APIRouter()
storage_service = StorageService()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    db: DbSession,
    file: UploadFile = File(...),
    account_id: UUID = Form(...),
    file_password: str | None = Form(None, description="Password for encrypted files (e.g. Nequi PDF). Stored encrypted."),
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

    # Save file and compute hash
    storage_uri, file_hash = storage_service.save_file(content, filename)

    # If a password was provided, encrypt and persist it on the account
    if file_password:
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.file_password = encrypt_password(file_password)
            db.add(account)

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
