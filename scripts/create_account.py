#!/usr/bin/env python
"""Helper script to create a test account."""

import sys

from app.db.session import SessionLocal
from app.models import Account


def create_account(
    bank_name: str = "Bancolombia",
    account_name: str = "Cuenta de Ahorros",
    currency: str = "COP",
):
    """Create a new account and print its ID."""
    db = SessionLocal()
    try:
        account = Account(
            bank_name=bank_name, account_name=account_name, currency=currency
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        print(f"✓ Created account with ID: {account.id}")
        print(f"  Bank: {account.bank_name}")
        print(f"  Name: {account.account_name}")
        print(f"  Currency: {account.currency}")
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
        currency = sys.argv[3] if len(sys.argv) > 3 else "COP"
        create_account(bank_name, account_name, currency)
    else:
        create_account()
