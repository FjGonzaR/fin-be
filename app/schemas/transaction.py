from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import Category, CategoryMethod


class TransactionResponse(BaseModel):
    id: UUID
    account_id: UUID
    source_file_id: UUID
    posted_at: date
    description_raw: str
    description_clean: str
    amount: Decimal
    currency: str
    merchant_guess: str | None
    details_json: dict | None
    category: Category | None
    category_confidence: Decimal | None
    category_method: CategoryMethod | None
    created_at: datetime

    model_config = {"from_attributes": True, "frozen": False}


class RecategorizeRequest(BaseModel):
    category: Category
    description_clean: str | None = None  # if provided, adds a new category_example
