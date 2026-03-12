"""add AHORROS to account_type_enum and INGRESO/INVERSION to category_enum

Revision ID: 009
Revises: 008
Create Date: 2026-03-12

Changes:
- Add 'AHORROS' value to account_type_enum
- Add 'INGRESO' and 'INVERSION' values to category_enum
"""
from typing import Sequence, Union

from alembic import op

revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE account_type_enum ADD VALUE IF NOT EXISTS 'AHORROS'")
    op.execute("ALTER TYPE category_enum ADD VALUE IF NOT EXISTS 'INGRESO'")
    op.execute("ALTER TYPE category_enum ADD VALUE IF NOT EXISTS 'INVERSION'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    pass
