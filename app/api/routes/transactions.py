from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

USD_TO_COP = Decimal("4000")

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.models import CategoryExample, Transaction
from app.models.enums import CategoryMethod
from app.schemas.transaction import RecategorizeRequest, TransactionResponse

router = APIRouter()


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    db: DbSession,
    account_id: UUID = Query(..., description="Account ID to filter by"),
    months: str | None = Query(None, description="Comma-separated YYYY-MM (e.g., 2024-01,2024-02)"),
):
    """
    List transactions for an account.

    Query params:
    - account_id: required
    - months: optional CSV of YYYY-MM
    """
    query = db.query(Transaction).filter(Transaction.account_id == account_id)

    # Filter by months if provided
    if months:
        month_list = [m.strip() for m in months.split(",")]
        # Convert YYYY-MM to date range filters
        from datetime import datetime

        filters = []
        for month_str in month_list:
            try:
                year, month = map(int, month_str.split("-"))
                # Get first and last day of month
                if month == 12:
                    start_date = datetime(year, month, 1).date()
                    end_date = datetime(year + 1, 1, 1).date()
                else:
                    start_date = datetime(year, month, 1).date()
                    end_date = datetime(year, month + 1, 1).date()

                filters.append(
                    (Transaction.posted_at >= start_date)
                    & (Transaction.posted_at < end_date)
                )
            except ValueError:
                continue  # Skip invalid month formats

        if filters:
            from sqlalchemy import or_

            query = query.filter(or_(*filters))

    # Order by posted_at descending
    query = query.order_by(Transaction.posted_at.desc())

    transactions = query.all()
    result = []
    for tx in transactions:
        response = TransactionResponse.model_validate(tx)
        if tx.currency == "USD":
            response.amount = (response.amount * USD_TO_COP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result.append(response)
    return result


@router.patch("/{transaction_id}/categorize", response_model=TransactionResponse)
def recategorize_transaction(
    transaction_id: UUID,
    body: RecategorizeRequest,
    db: DbSession,
):
    """
    Manually reclassify a transaction.
    Optionally seeds a new category_example from description_clean.
    """
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.category = body.category
    tx.category_confidence = Decimal("1.00")
    tx.category_method = CategoryMethod.USER

    if body.description_clean:
        exists = (
            db.query(CategoryExample)
            .filter(
                CategoryExample.description_clean == body.description_clean,
                CategoryExample.category == body.category,
            )
            .first()
        )
        if not exists:
            db.add(CategoryExample(description_clean=body.description_clean, category=body.category))

    db.commit()
    db.refresh(tx)
    return TransactionResponse.model_validate(tx)
