from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.models import Account
from app.models.enums import AccountTypeEnum, BankEnum, OwnerEnum
from pydantic import BaseModel

router = APIRouter()


class AccountCreate(BaseModel):
    bank_name: BankEnum
    account_name: str
    owner: OwnerEnum
    account_type: AccountTypeEnum


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
