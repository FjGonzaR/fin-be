from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, contains_eager

from app.models.account import Account
from app.models.enums import Category, OwnerEnum
from app.models.source_file import SourceFile
from app.models.transaction import Transaction

USD_TO_COP = Decimal("4000")


def apply_transaction_filters(
    q,
    owner: OwnerEnum | None,
    account_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
    category: Category | None = None,
):
    """Apply common filters to a query that already has SourceFile and Account joined."""
    if owner:
        q = q.filter(Account.owner == owner)
    if account_id:
        q = q.filter(SourceFile.account_id == account_id)
    if date_from:
        q = q.filter(Transaction.posted_at >= date_from)
    if date_to:
        q = q.filter(Transaction.posted_at <= date_to)
    if category:
        q = q.filter(Transaction.category == category)
    return q


def build_transaction_query(
    db: Session,
    owner: OwnerEnum | None,
    account_id: UUID | None,
    date_from: date | None = None,
    date_to: date | None = None,
    category: Category | None = None,
):
    """Return ORM query of Transaction with source_file and account eagerly loaded."""
    q = (
        db.query(Transaction)
        .join(SourceFile, Transaction.source_file_id == SourceFile.id)
        .join(Account, SourceFile.account_id == Account.id)
        .options(
            contains_eager(Transaction.source_file).contains_eager(SourceFile.account)
        )
    )
    return apply_transaction_filters(q, owner, account_id, date_from, date_to, category)
