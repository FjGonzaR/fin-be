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
    months: str | None = Query(None),
    category: Category | None = Query(None),
):
    transactions = build_transaction_query(db, owner, account_id, months, category).all()

    total_spent = Decimal("0")
    total_abonos = Decimal("0")
    expense_count = 0
    abono_count = 0
    months_seen: set[str] = set()

    for tx in transactions:
        amt = tx.amount
        if tx.currency == "USD":
            amt = (amt * USD_TO_COP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        months_seen.add(tx.posted_at.strftime("%Y-%m"))
        if amt < 0:
            total_spent += abs(amt)
            expense_count += 1
        else:
            total_abonos += amt
            abono_count += 1

    transaction_count = expense_count + abono_count
    num_months = len(months_seen)
    avg_monthly_spend = (total_spent / num_months).quantize(Decimal("0.01")) if num_months else None

    return KPIResponse(
        total_spent=total_spent,
        total_abonos=total_abonos,
        net=total_abonos - total_spent,
        transaction_count=transaction_count,
        expense_count=expense_count,
        abono_count=abono_count,
        avg_monthly_spend=avg_monthly_spend,
    )


@router.get("/histogram", response_model=list[HistogramPoint])
def get_histogram(
    db: DbSession,
    owner: OwnerEnum | None = Query(None),
    account_id: UUID | None = Query(None),
    months: str | None = Query(None),
    category: Category | None = Query(None),
):
    spent_expr = func.sum(case((_amount_cop < 0, -_amount_cop), else_=0))
    income_expr = func.sum(case((_amount_cop > 0, _amount_cop), else_=0))
    month_label = func.to_char(Transaction.posted_at, "YYYY-MM").label("month")

    q = (
        db.query(month_label, spent_expr.label("total_spent"), income_expr.label("total_abonos"))
        .join(SourceFile, Transaction.source_file_id == SourceFile.id)
        .join(Account, SourceFile.account_id == Account.id)
    )
    q = apply_transaction_filters(q, owner, account_id, months, category)
    rows = q.group_by("month").order_by("month").all()

    return [
        HistogramPoint(
            month=row.month,
            total_spent=Decimal(str(row.total_spent or 0)),
            total_abonos=Decimal(str(row.total_abonos or 0)),
        )
        for row in rows
    ]


@router.get("/by-category", response_model=list[CategoryBreakdownItem])
def get_by_category(
    db: DbSession,
    owner: OwnerEnum | None = Query(None),
    account_id: UUID | None = Query(None),
    months: str | None = Query(None),
    category: Category | None = Query(None),
):
    total_expr = func.sum(-_amount_cop).label("total")
    count_expr = func.count().label("count")

    q = (
        db.query(Transaction.category, total_expr, count_expr)
        .join(SourceFile, Transaction.source_file_id == SourceFile.id)
        .join(Account, SourceFile.account_id == Account.id)
        .filter(_amount_cop < 0)
    )
    q = apply_transaction_filters(q, owner, account_id, months, category)
    rows = q.group_by(Transaction.category).order_by(total_expr.desc()).all()

    grand_total = sum(Decimal(str(r.total or 0)) for r in rows)

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
    months: str | None = Query(None),
    category: Category | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    q = (
        build_transaction_query(db, owner, account_id, months, category)
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
