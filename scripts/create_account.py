#!/usr/bin/env python
"""Helper script to create a test account."""

import sys

from app.db.session import SessionLocal
from app.models import Account
from app.models.enums import AccountTypeEnum, BankEnum, OwnerEnum


def create_account(
    bank_name: str = "BANCOLOMBIA",
    account_name: str = "Cuenta de Ahorros",
    owner: str = "PACHO",
    account_type: str = "CREDITO",
):
    """Create a new account and print its ID."""
    try:
        bank = BankEnum(bank_name.upper())
    except ValueError:
        print(f"✗ Invalid bank_name '{bank_name}'. Valid values: {[e.value for e in BankEnum]}")
        sys.exit(1)

    try:
        owner_val = OwnerEnum(owner.upper())
    except ValueError:
        print(f"✗ Invalid owner '{owner}'. Valid values: {[e.value for e in OwnerEnum]}")
        sys.exit(1)

    try:
        account_type_val = AccountTypeEnum(account_type.upper())
    except ValueError:
        print(f"✗ Invalid account_type '{account_type}'. Valid values: {[e.value for e in AccountTypeEnum]}")
        sys.exit(1)

    db = SessionLocal()
    try:
        account = Account(
            bank_name=bank,
            account_name=account_name,
            owner=owner_val,
            account_type=account_type_val,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        print(f"✓ Created account with ID: {account.id}")
        print(f"  Bank:  {account.bank_name}")
        print(f"  Name:  {account.account_name}")
        print(f"  Owner: {account.owner}")
        print(f"  Type:  {account.account_type}")
        return account.id
    except Exception as e:
        print(f"✗ Failed to create account: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        bank_name = sys.argv[1]
        account_name = sys.argv[2] if len(sys.argv) > 2 else "Cuenta"
        owner = sys.argv[3] if len(sys.argv) > 3 else "PACHO"
        account_type = sys.argv[4] if len(sys.argv) > 4 else "CREDITO"
        create_account(bank_name, account_name, owner, account_type)
    else:
        create_account()
