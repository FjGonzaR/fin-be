from pydantic import BaseModel


class ETLProcessResponse(BaseModel):
    parsed_rows: int
    inserted_transactions: int
    duplicates_skipped: int
    status: str
