from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AccountTypeEnum, BankEnum, OwnerEnum
from app.schemas.types import DateAsLocalISO, DecimalAsFloat


class KPIResponse(BaseModel):
    total_ingresos: DecimalAsFloat
    total_gastos: DecimalAsFloat
    total_pagos: DecimalAsFloat
    total_inversiones: DecimalAsFloat
    net: DecimalAsFloat
    transaction_count: int
    avg_monthly_spend: DecimalAsFloat | None


class HistogramPoint(BaseModel):
    week: str  # "YYYY-Www"
    total_spent: DecimalAsFloat


class CategoryBreakdownItem(BaseModel):
    category: str | None  # enum name or "SIN_CATEGORIZAR"
    total: DecimalAsFloat
    percentage: DecimalAsFloat
    count: int


class TopTransactionItem(BaseModel):
    id: UUID
    posted_at: DateAsLocalISO
    description_clean: str
    amount: DecimalAsFloat  # COP, always positive (abs)
    category: str | None
    merchant_guess: str | None
    account_name: str
    bank_name: BankEnum
    owner: OwnerEnum
    account_type: AccountTypeEnum
