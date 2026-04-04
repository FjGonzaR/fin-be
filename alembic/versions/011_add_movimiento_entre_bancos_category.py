"""add MOVIMIENTO_ENTRE_BANCOS to category_enum

Revision ID: 011
Revises: 010
Create Date: 2026-04-04

Changes:
- Add 'MOVIMIENTO_ENTRE_BANCOS' value to category_enum PostgreSQL type
"""
from typing import Sequence, Union

from alembic import op

revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE category_enum ADD VALUE IF NOT EXISTS 'MOVIMIENTO_ENTRE_BANCOS'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    pass
