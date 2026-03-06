from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.etl.pipeline import ETLPipeline
from app.models import RawRow, SourceFile, Transaction
from app.schemas.etl import ETLProcessResponse

router = APIRouter()


@router.post("/process/{file_id}", response_model=ETLProcessResponse)
def process_etl(
    file_id: UUID,
    db: DbSession,
):
    """
    Process ETL for a source file.
    """
    try:
        pipeline = ETLPipeline(db)
        result = pipeline.process_file(file_id)
        return ETLProcessResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ETL processing failed: {str(e)}")


@router.delete("/reset/{file_id}")
def reset_etl(file_id: UUID, db: DbSession):
    """
    Delete all transactions and raw rows for a source file and reset its status to UPLOADED.
    """
    source_file = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not source_file:
        raise HTTPException(status_code=404, detail=f"Source file {file_id} not found")

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
