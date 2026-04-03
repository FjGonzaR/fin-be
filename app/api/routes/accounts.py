from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.models import Account, RawRow, SourceFile, Transaction
from app.models.enums import AccountTypeEnum, BankEnum, OwnerEnum
from pydantic import BaseModel

router = APIRouter()


class AccountCreate(BaseModel):
    bank_name: BankEnum
    account_name: str
    owner: OwnerEnum
    account_type: AccountTypeEnum


class AccountUpdate(BaseModel):
    bank_name: BankEnum | None = None
    account_name: str | None = None
    owner: OwnerEnum | None = None
    account_type: AccountTypeEnum | None = None


class AccountResponse(BaseModel):
    id: UUID
    bank_name: BankEnum
    account_name: str
    owner: OwnerEnum
    account_type: AccountTypeEnum

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    db: DbSession,
    owner: OwnerEnum | None = Query(None, description="Filter by owner"),
):
    q = db.query(Account)
    if owner:
        q = q.filter(Account.owner == owner)
    return q.all()


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(body: AccountCreate, db: DbSession):
    account = Account(
        bank_name=body.bank_name,
        account_name=body.account_name,
        owner=body.owner,
        account_type=body.account_type,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: UUID, db: DbSession):
    """Get a single account by ID."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: UUID, body: AccountUpdate, db: DbSession):
    """Update one or more fields of an account."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: UUID, db: DbSession):
    """
    Delete an account and cascade-delete all associated source files,
    transactions, and raw rows.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    source_files = (
        db.query(SourceFile).filter(SourceFile.account_id == account_id).all()
    )
    for sf in source_files:
        db.query(Transaction).filter(Transaction.source_file_id == sf.id).delete()
        db.query(RawRow).filter(RawRow.source_file_id == sf.id).delete()
    db.query(SourceFile).filter(SourceFile.account_id == account_id).delete()

    db.delete(account)
    db.commit()
