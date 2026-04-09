from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import case, func

from app.api.deps import DbSession
from app.api.query_helpers import USD_TO_COP, apply_transaction_filters, build_transaction_query
from app.models.account import Account
from app.models.enums import Category, OwnerEnum
from app.models.source_file import SourceFile
from app.models.transaction import Transaction
from app.schemas.dashboard import (
    CategoryBreakdownItem,
    HistogramPoint,
    KPIResponse,
    TopTransactionItem,
)

router = APIRouter()

# SQLAlchemy expression: amount converted to COP
_amount_cop = case(
    (Transaction.currency == "USD", Transaction.amount * 4000),
    else_=Transaction.amount,
)


@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    db: DbSession,
    owner: OwnerEnum | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: Category | None = Query(None),
):
    transactions = build_transaction_query(db, owner, account_id, date_from, date_to, category).all()

    total_ingresos = Decimal("0")
    total_gastos = Decimal("0")
    total_pagos = Decimal("0")
    total_inversiones = Decimal("0")
    days_seen: set[date] = set()

    _PAGO_CATEGORIES = {Category.PAGO}
    _INVERSION_CATEGORIES = {Category.INVERSION}
    _INGRESO_CATEGORIES = {Category.INGRESO}
    _EXCLUDE_FROM_GASTOS = {Category.PAGO, Category.INVERSION, Category.INGRESO, Category.MOVIMIENTO_ENTRE_BANCOS}

    for tx in transactions:
        amt = tx.amount
        if tx.currency == "USD":
            amt = (amt * USD_TO_COP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        days_seen.add(tx.posted_at)

        if tx.category in _INGRESO_CATEGORIES:
            total_ingresos += amt
        elif tx.category in _PAGO_CATEGORIES:
            total_pagos += abs(amt)
        elif tx.category in _INVERSION_CATEGORIES:
            total_inversiones += abs(amt)
        elif tx.category not in _EXCLUDE_FROM_GASTOS:
            if amt < 0:
                total_gastos += abs(amt)
            else:
                # Credit/refund within a spending category (e.g. OCIO refund).
                # Not a true INGRESO but counts as an entrada toward the net.
                total_ingresos += amt

    num_days = len(days_seen)
    avg_daily_spend = (total_gastos / num_days).quantize(Decimal("0.01")) if num_days else None

    return KPIResponse(
        total_ingresos=total_ingresos,
        total_gastos=total_gastos,
        total_pagos=total_pagos,
        total_inversiones=total_inversiones,
        net=total_ingresos - total_gastos - total_inversiones,
        transaction_count=len(transactions),
        avg_daily_spend=avg_daily_spend,
    )


@router.get("/histogram", response_model=list[HistogramPoint])
def get_histogram(
    db: DbSession,
    owner: OwnerEnum | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: Category | None = Query(None),
):
    spent_expr = func.sum(case((_amount_cop < 0, -_amount_cop), else_=0))
    week_label = func.to_char(func.date_trunc("week", Transaction.posted_at), "YYYY-MM-DD").label("week")

    q = (
        db.query(week_label, spent_expr.label("total_spent"))
        .join(SourceFile, Transaction.source_file_id == SourceFile.id)
        .join(Account, SourceFile.account_id == Account.id)
    )
    q = apply_transaction_filters(q, owner, account_id, date_from, date_to, category)
    q = q.filter(Transaction.category != Category.PAGO)
    rows = q.group_by("week").order_by("week").all()

    return [
        HistogramPoint(
            week=row.week,
            total_spent=Decimal(str(row.total_spent or 0)),
        )
        for row in rows
    ]


@router.get("/by-category", response_model=list[CategoryBreakdownItem])
def get_by_category(
    db: DbSession,
    owner: OwnerEnum | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: Category | None = Query(None),
):
    total_expr = func.sum(-_amount_cop).label("total")
    count_expr = func.count().label("count")

    q = (
        db.query(Transaction.category, total_expr, count_expr)
        .join(SourceFile, Transaction.source_file_id == SourceFile.id)
        .join(Account, SourceFile.account_id == Account.id)
        .filter(Transaction.category.notin_([Category.PAGO, Category.INGRESO, Category.INVERSION]))
        .filter(_amount_cop < 0)
    )
    q = apply_transaction_filters(q, owner, account_id, date_from, date_to, category)
    rows = q.group_by(Transaction.category).order_by(total_expr.desc()).all()

    grand_total = sum(Decimal(str(r.total or 0)) for r in rows if (r.total or 0) > 0)

    result = []
    for row in rows:
        total = Decimal(str(row.total or 0))
        percentage = (total / grand_total * 100).quantize(Decimal("0.01")) if grand_total else Decimal("0")
        result.append(
            CategoryBreakdownItem(
                category=row.category.value if row.category else "SIN_CATEGORIZAR",
                total=total,
                percentage=percentage,
                count=row.count,
            )
        )
    return result


@router.get("/top-transactions", response_model=list[TopTransactionItem])
def get_top_transactions(
    db: DbSession,
    owner: OwnerEnum | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: Category | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    q = (
        build_transaction_query(db, owner, account_id, date_from, date_to, category)
        .filter(_amount_cop < 0)
        .order_by(_amount_cop.asc())
        .limit(limit)
    )
    transactions = q.all()

    result = []
    for tx in transactions:
        account = tx.source_file.account
        amt = tx.amount
        if tx.currency == "USD":
            amt = (amt * USD_TO_COP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result.append(
            TopTransactionItem(
                id=tx.id,
                posted_at=tx.posted_at,
                description_clean=tx.description_clean,
                amount=abs(amt),
                category=tx.category.value if tx.category else None,
                merchant_guess=tx.merchant_guess,
                account_name=account.account_name,
                bank_name=account.bank_name,
                owner=account.owner,
                account_type=account.account_type,
            )
        )
    return result
