"""add FALABELLA to bank_enum

Revision ID: 006
Revises: 005
Create Date: 2026-03-06

Changes:
- Add 'FALABELLA' value to bank_enum PostgreSQL type
"""
from typing import Sequence, Union

from alembic import op

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE bank_enum ADD VALUE IF NOT EXISTS 'FALABELLA'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    # To truly roll back, the enum would need to be recreated — out of scope here.
    pass
