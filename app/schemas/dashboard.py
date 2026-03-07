from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AccountTypeEnum, BankEnum, OwnerEnum
from app.schemas.types import DecimalAsFloat


class KPIResponse(BaseModel):
    total_spent: DecimalAsFloat
    total_abonos: DecimalAsFloat
    net: DecimalAsFloat
    transaction_count: int
    expense_count: int
    abono_count: int
    avg_monthly_spend: DecimalAsFloat | None


class HistogramPoint(BaseModel):
    month: str  # "YYYY-MM"
    total_spent: DecimalAsFloat
    total_abonos: DecimalAsFloat


class CategoryBreakdownItem(BaseModel):
    category: str | None  # enum name or "SIN_CATEGORIZAR"
    total: DecimalAsFloat
    percentage: DecimalAsFloat
    count: int


class TopTransactionItem(BaseModel):
    id: UUID
    posted_at: date
    description_clean: str
    amount: DecimalAsFloat  # COP, always positive (abs)
    category: str | None
    merchant_guess: str | None
    account_name: str
    bank_name: BankEnum
    owner: OwnerEnum
    account_type: AccountTypeEnum
