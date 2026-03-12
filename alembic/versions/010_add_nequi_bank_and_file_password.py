"""add NEQUI to bank_enum and file_password to accounts

Revision ID: 010
Revises: 009
Create Date: 2026-03-12

Changes:
- Add 'NEQUI' value to bank_enum PostgreSQL type
- Add nullable file_password column to accounts (for password-protected files)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE bank_enum ADD VALUE IF NOT EXISTS 'NEQUI'")
    op.add_column('accounts', sa.Column('file_password', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'file_password')
    # PostgreSQL does not support removing values from an enum type.
