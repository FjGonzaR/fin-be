from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AccountTypeEnum, BankEnum, Category, CategoryMethod, OwnerEnum
from app.schemas.types import DecimalAsFloat


class TransactionResponse(BaseModel):
    id: UUID
    source_file_id: UUID
    posted_at: date
    description_raw: str
    description_clean: str
    amount: DecimalAsFloat
    currency: str
    merchant_guess: str | None
    details_json: dict | None
    category: Category | None
    category_confidence: DecimalAsFloat | None
    category_method: CategoryMethod | None
    created_at: datetime
    # Account fields
    account_id: UUID
    account_name: str
    bank_name: BankEnum
    owner: OwnerEnum
    account_type: AccountTypeEnum

    model_config = {"from_attributes": True, "frozen": False}


class RecategorizeRequest(BaseModel):
    category: Category
    description_clean: str | None = None  # if provided, adds a new category_example
