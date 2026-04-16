from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.etl.pipeline import ETLPipeline
from app.models import RawRow, SourceFile, Transaction
from app.models.account import Account
from app.schemas.etl import ETLProcessResponse

router = APIRouter()


def _get_file_or_404(file_id: UUID, db, current_user) -> SourceFile:
    source_file = (
        db.query(SourceFile)
        .join(Account, SourceFile.account_id == Account.id)
        .filter(SourceFile.id == file_id)
        .first()
    )
    if not source_file:
        raise HTTPException(status_code=404, detail=f"Source file {file_id} not found")
    if not current_user.is_admin and source_file.account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Source file {file_id} not found")
    return source_file


@router.post("/process/{file_id}", response_model=ETLProcessResponse)
def process_etl(
    file_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Process ETL for a source file.
    """
    _get_file_or_404(file_id, db, current_user)
    try:
        pipeline = ETLPipeline(db)
        result = pipeline.process_file(file_id)
        return ETLProcessResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL processing failed: {str(e)}")


@router.delete("/reset/{file_id}")
def reset_etl(file_id: UUID, db: DbSession, current_user: CurrentUser):
    """
    Delete all transactions and raw rows for a source file and reset its status to UPLOADED.
    """
    source_file = _get_file_or_404(file_id, db, current_user)

    deleted_tx = (
        db.query(Transaction).filter(Transaction.source_file_id == file_id).delete()
    )
    deleted_rows = (
        db.query(RawRow).filter(RawRow.source_file_id == file_id).delete()
    )
    source_file.parse_status = "UPLOADED"
    db.commit()

    return {
        "file_id": file_id,
        "deleted_transactions": deleted_tx,
        "deleted_raw_rows": deleted_rows,
        "status": "UPLOADED",
    }
