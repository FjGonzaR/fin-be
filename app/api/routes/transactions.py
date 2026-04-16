from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession
from app.api.query_helpers import USD_TO_COP, build_transaction_query
from app.models import CategoryExample, Transaction
from app.models.enums import Category, CategoryMethod
from app.schemas.transaction import RecategorizeRequest, TransactionResponse

router = APIRouter()


def _serialize_tx(tx) -> TransactionResponse:
    account = tx.source_file.account
    amt = tx.amount
    if tx.currency == "USD":
        amt = (amt * USD_TO_COP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return TransactionResponse.model_validate({
        **{k: v for k, v in tx.__dict__.items() if not k.startswith("_")},
        "amount": amt,
        "account_id": account.id,
        "account_name": account.account_name,
        "bank_name": account.bank_name,
        "owner": account.owner,
        "account_type": account.account_type,
    })


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    db: DbSession,
    current_user: CurrentUser,
    account_id: UUID | None = Query(None, description="Account ID to filter by"),
    owner: str | None = Query(None, description="Owner label to filter by"),
    date_from: date | None = Query(None, description="Start date (inclusive), format YYYY-MM-DD"),
    date_to: date | None = Query(None, description="End date (inclusive), format YYYY-MM-DD"),
    category: Category | None = Query(None, description="Filter by category"),
):
    user_id = None if current_user.is_admin else current_user.id
    query = build_transaction_query(db, user_id, owner, account_id, date_from, date_to, category)
    query = query.order_by(Transaction.posted_at.desc())
    return [_serialize_tx(tx) for tx in query.all()]


@router.patch("/{transaction_id}/categorize", response_model=TransactionResponse)
def recategorize_transaction(
    transaction_id: UUID,
    body: RecategorizeRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Manually reclassify a transaction.
    Optionally seeds a new category_example from description_clean.
    """
    user_id = None if current_user.is_admin else current_user.id
    tx = (
        build_transaction_query(db, user_id, None, None, None)
        .filter(Transaction.id == transaction_id)
        .first()
    )
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
    return _serialize_tx(tx)
