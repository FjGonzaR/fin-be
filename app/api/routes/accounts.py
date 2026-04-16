from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession
from app.models import Account, RawRow, SourceFile, Transaction
from app.models.enums import AccountTypeEnum, BankEnum
from pydantic import BaseModel

router = APIRouter()


class AccountCreate(BaseModel):
    bank_name: BankEnum
    account_name: str
    owner: str
    account_type: AccountTypeEnum


class AccountUpdate(BaseModel):
    bank_name: BankEnum | None = None
    account_name: str | None = None
    owner: str | None = None
    account_type: AccountTypeEnum | None = None


class AccountResponse(BaseModel):
    id: UUID
    bank_name: BankEnum
    account_name: str
    owner: str
    account_type: AccountTypeEnum
    user_id: UUID | None

    model_config = {"from_attributes": True}


def _check_ownership(account: Account, current_user) -> None:
    """Raise 404 if the non-admin user doesn't own the account."""
    if not current_user.is_admin and account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Account not found")


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    db: DbSession,
    current_user: CurrentUser,
    owner: str | None = Query(None, description="Filter by owner label"),
):
    q = db.query(Account)
    if not current_user.is_admin:
        q = q.filter(Account.user_id == current_user.id)
    if owner:
        q = q.filter(Account.owner == owner)
    return q.all()


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(body: AccountCreate, db: DbSession, current_user: CurrentUser):
    account = Account(
        bank_name=body.bank_name,
        account_name=body.account_name,
        owner=body.owner,
        account_type=body.account_type,
        user_id=current_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: UUID, db: DbSession, current_user: CurrentUser):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _check_ownership(account, current_user)
    return account


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: UUID, body: AccountUpdate, db: DbSession, current_user: CurrentUser):
    """Update one or more fields of an account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _check_ownership(account, current_user)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: UUID, db: DbSession, current_user: CurrentUser):
    """
    Delete an account and cascade-delete all associated source files,
    transactions, and raw rows.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _check_ownership(account, current_user)

    source_files = (
        db.query(SourceFile).filter(SourceFile.account_id == account_id).all()
    )
    for sf in source_files:
        db.query(Transaction).filter(Transaction.source_file_id == sf.id).delete()
        db.query(RawRow).filter(RawRow.source_file_id == sf.id).delete()
    db.query(SourceFile).filter(SourceFile.account_id == account_id).delete()

    db.delete(account)
    db.commit()
