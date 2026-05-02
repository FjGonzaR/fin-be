from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.models.enums import AccountTypeEnum, BankEnum, CategoryMethod
from app.schemas.types import DateAsLocalISO, DecimalAsFloat


class TransactionResponse(BaseModel):
    id: UUID
    source_file_id: UUID
    posted_at: DateAsLocalISO
    description_raw: str
    description_clean: str
    amount: DecimalAsFloat
    currency: str
    merchant_guess: str | None
    details_json: dict | None
    category_id: UUID | None
    category: str | None  # slug, kept for backwards-compatibility with frontend
    category_confidence: DecimalAsFloat | None
    category_method: CategoryMethod | None
    created_at: datetime
    # Account fields
    account_id: UUID
    account_name: str
    bank_name: BankEnum
    owner: str
    account_type: AccountTypeEnum

    model_config = {"from_attributes": True, "frozen": False}


class RecategorizeRequest(BaseModel):
    """Reclassify a transaction. Provide either category_id or category_slug."""
    category_id: UUID | None = None
    category_slug: str | None = None
    description_clean: str | None = None  # optional; falls back to tx.description_clean

    @model_validator(mode="after")
    def _require_one(self) -> "RecategorizeRequest":
        if not self.category_id and not self.category_slug:
            raise ValueError("category_id or category_slug is required")
        return self
