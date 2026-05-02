from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession
from app.api.query_helpers import USD_TO_COP, build_transaction_query
from app.etl.keyword_learner import learn_from_reclassification
from app.models import Category, CategoryExample, Transaction
from app.models.enums import CategoryMethod
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
        "category": tx.category.slug if tx.category else None,
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
    category: str | None = Query(None, description="Filter by category slug"),
):
    user_id = None if current_user.is_admin else current_user.id
    query = build_transaction_query(db, user_id, owner, account_id, date_from, date_to, category)
    query = query.order_by(Transaction.posted_at.desc())
    return [_serialize_tx(tx) for tx in query.all()]


def _resolve_category(db, body: RecategorizeRequest) -> Category:
    if body.category_id:
        cat = db.query(Category).filter(Category.id == body.category_id).first()
    else:
        cat = db.query(Category).filter(Category.slug == body.category_slug).first()
    if not cat or not cat.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


@router.patch("/{transaction_id}/categorize", response_model=TransactionResponse)
def recategorize_transaction(
    transaction_id: UUID,
    body: RecategorizeRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Manually reclassify a transaction. Always upserts a CategoryExample so the
    classifier learns from this reclassification, and runs the keyword learner
    to promote recurring tokens to LEARNED keywords.
    """
    user_id = None if current_user.is_admin else current_user.id
    tx = (
        build_transaction_query(db, user_id, None, None, None)
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    category = _resolve_category(db, body)

    tx.category_id = category.id
    tx.category_confidence = Decimal("1.00")
    tx.category_method = CategoryMethod.USER

    description_clean = body.description_clean or tx.description_clean
    if description_clean:
        existing = (
            db.query(CategoryExample)
            .filter(
                CategoryExample.description_clean == description_clean,
                CategoryExample.category_id == category.id,
            )
            .first()
        )
        if not existing:
            db.add(CategoryExample(description_clean=description_clean, category_id=category.id))
            db.flush()
        learn_from_reclassification(db, description_clean, category.id)

    db.commit()
    db.refresh(tx)
    return _serialize_tx(tx)
