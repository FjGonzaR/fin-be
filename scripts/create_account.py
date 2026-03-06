#!/usr/bin/env python
"""Helper script to create a test account."""

import sys

from app.db.session import SessionLocal
from app.models import Account
from app.models.enums import BankEnum


def create_account(
    bank_name: str = "BANCOLOMBIA",
    account_name: str = "Cuenta de Ahorros",
):
    """Create a new account and print its ID."""
    try:
        bank = BankEnum(bank_name.upper())
    except ValueError:
        print(f"✗ Invalid bank_name '{bank_name}'. Valid values: {[e.value for e in BankEnum]}")
        sys.exit(1)

    db = SessionLocal()
    try:
        account = Account(bank_name=bank, account_name=account_name)
        db.add(account)
        db.commit()
        db.refresh(account)
        print(f"✓ Created account with ID: {account.id}")
        print(f"  Bank: {account.bank_name}")
        print(f"  Name: {account.account_name}")
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
        create_account(bank_name, account_name)
    else:
        create_account()
