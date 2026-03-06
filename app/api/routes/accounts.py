from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import Account
from pydantic import BaseModel

router = APIRouter()


class AccountCreate(BaseModel):
    bank_name: str
    account_name: str


class AccountResponse(BaseModel):
    id: UUID
    bank_name: str
    account_name: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AccountResponse])
def list_accounts(db: DbSession):
    return db.query(Account).all()


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(body: AccountCreate, db: DbSession):
    account = Account(
        bank_name=body.bank_name,
        account_name=body.account_name,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
