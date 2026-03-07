"""add owner and account_type to accounts

Revision ID: 005
Revises: 004
Create Date: 2026-03-06

Changes:
- Create owner_enum (PACHO, LU) and account_type_enum (CREDITO, DEBITO)
- Add owner and account_type columns to accounts
- Migrate existing accounts to owner=PACHO, account_type=CREDITO
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

owner_enum = PgEnum('PACHO', 'LU', name='owner_enum', create_type=True)
account_type_enum = PgEnum('CREDITO', 'DEBITO', name='account_type_enum', create_type=True)


def upgrade() -> None:
    owner_enum.create(op.get_bind(), checkfirst=True)
    account_type_enum.create(op.get_bind(), checkfirst=True)

    owner_ref = PgEnum('PACHO', 'LU', name='owner_enum', create_type=False)
    account_type_ref = PgEnum('CREDITO', 'DEBITO', name='account_type_enum', create_type=False)

    op.add_column('accounts', sa.Column('owner', owner_ref, nullable=True))
    op.add_column('accounts', sa.Column('account_type', account_type_ref, nullable=True))

    # Migrate all existing accounts to PACHO / CREDITO
    op.execute("UPDATE accounts SET owner = 'PACHO', account_type = 'CREDITO'")

    op.alter_column('accounts', 'owner', nullable=False)
    op.alter_column('accounts', 'account_type', nullable=False)


def downgrade() -> None:
    op.drop_column('accounts', 'account_type')
    op.drop_column('accounts', 'owner')
    PgEnum(name='account_type_enum').drop(op.get_bind(), checkfirst=True)
    PgEnum(name='owner_enum').drop(op.get_bind(), checkfirst=True)
