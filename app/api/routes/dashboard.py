from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import case, func
from sqlalchemy.orm import aliased

from app.api.deps import CurrentUser, DbSession
from app.api.query_helpers import USD_TO_COP, apply_transaction_filters, build_transaction_query
from app.models.account import Account
from app.models.category import Category
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

# Slug-based behavior (mirrors the old Category enum constants).
_PAGO_SLUGS = {"PAGO"}
_INVERSION_SLUGS = {"INVERSION"}
_INGRESO_SLUGS = {"INGRESO"}
_EXCLUDE_FROM_GASTOS_SLUGS = {"PAGO", "INVERSION", "INGRESO", "MOVIMIENTO_ENTRE_BANCOS"}


@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    db: DbSession,
    current_user: CurrentUser,
    owner: str | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: str | None = Query(None),
):
    user_id = None if current_user.is_admin else current_user.id
    transactions = build_transaction_query(db, user_id, owner, account_id, date_from, date_to, category).all()

    total_ingresos = Decimal("0")
    total_gastos = Decimal("0")
    total_pagos = Decimal("0")
    total_inversiones = Decimal("0")
    days_seen: set[date] = set()

    for tx in transactions:
        amt = tx.amount
        if tx.currency == "USD":
            amt = (amt * USD_TO_COP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        days_seen.add(tx.posted_at)

        slug = tx.category.slug if tx.category else None

        if slug in _INGRESO_SLUGS:
            total_ingresos += amt
        elif slug in _PAGO_SLUGS:
            total_pagos += abs(amt)
        elif slug in _INVERSION_SLUGS:
            total_inversiones += abs(amt)
        elif slug not in _EXCLUDE_FROM_GASTOS_SLUGS:
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
    current_user: CurrentUser,
    owner: str | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: str | None = Query(None),
):
    user_id = None if current_user.is_admin else current_user.id
    spent_expr = func.sum(case((_amount_cop < 0, -_amount_cop), else_=0))
    week_label = func.to_char(func.date_trunc("week", Transaction.posted_at), "YYYY-MM-DD").label("week")

    cat_alias = aliased(Category)
    q = (
        db.query(week_label, spent_expr.label("total_spent"))
        .join(SourceFile, Transaction.source_file_id == SourceFile.id)
        .join(Account, SourceFile.account_id == Account.id)
        .outerjoin(cat_alias, Transaction.category_id == cat_alias.id)
    )
    q = apply_transaction_filters(q, user_id, owner, account_id, date_from, date_to, category)
    q = q.filter((cat_alias.slug != "PAGO") | (cat_alias.slug.is_(None)))
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
    current_user: CurrentUser,
    owner: str | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: str | None = Query(None),
):
    user_id = None if current_user.is_admin else current_user.id
    total_expr = func.sum(-_amount_cop).label("total")
    count_expr = func.count().label("count")

    cat_alias = aliased(Category)
    q = (
        db.query(cat_alias.slug.label("slug"), total_expr, count_expr)
        .join(SourceFile, Transaction.source_file_id == SourceFile.id)
        .join(Account, SourceFile.account_id == Account.id)
        .outerjoin(cat_alias, Transaction.category_id == cat_alias.id)
        .filter(
            (cat_alias.slug.is_(None))
            | (~cat_alias.slug.in_(["PAGO", "INGRESO", "INVERSION"]))
        )
        .filter(_amount_cop < 0)
    )
    q = apply_transaction_filters(q, user_id, owner, account_id, date_from, date_to, category)
    rows = q.group_by(cat_alias.slug).order_by(total_expr.desc()).all()

    grand_total = sum(Decimal(str(r.total or 0)) for r in rows if (r.total or 0) > 0)

    result = []
    for row in rows:
        total = Decimal(str(row.total or 0))
        percentage = (total / grand_total * 100).quantize(Decimal("0.01")) if grand_total else Decimal("0")
        result.append(
            CategoryBreakdownItem(
                category=row.slug if row.slug else "SIN_CATEGORIZAR",
                total=total,
                percentage=percentage,
                count=row.count,
            )
        )
    return result


@router.get("/top-transactions", response_model=list[TopTransactionItem])
def get_top_transactions(
    db: DbSession,
    current_user: CurrentUser,
    owner: str | None = Query(None),
    account_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    user_id = None if current_user.is_admin else current_user.id
    q = (
        build_transaction_query(db, user_id, owner, account_id, date_from, date_to, category)
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
                category=tx.category.slug if tx.category else None,
                merchant_guess=tx.merchant_guess,
                account_name=account.account_name,
                bank_name=account.bank_name,
                owner=account.owner,
                account_type=account.account_type,
            )
        )
    return result
