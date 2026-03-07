from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.api.query_helpers import USD_TO_COP, build_transaction_query
from app.models import CategoryExample, Transaction
from app.models.enums import Category, CategoryMethod, OwnerEnum
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
    account_id: UUID | None = Query(None, description="Account ID to filter by"),
    owner: OwnerEnum | None = Query(None, description="Owner to filter by"),
    months: str | None = Query(None, description="Comma-separated YYYY-MM (e.g., 2024-01,2024-02)"),
    category: Category | None = Query(None, description="Filter by category"),
):
    """
    List transactions.

    Query params:
    - account_id: optional
    - owner: optional
    - months: optional CSV of YYYY-MM
    - category: optional
    """
    query = build_transaction_query(db, owner, account_id, months, category)
    query = query.order_by(Transaction.posted_at.desc())
    return [_serialize_tx(tx) for tx in query.all()]


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
    tx = (
        build_transaction_query(db, None, None, None)
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
