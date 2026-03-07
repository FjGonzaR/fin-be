"""add PLATAFORMAS to category_enum

Revision ID: 007
Revises: 006
Create Date: 2026-03-07

Changes:
- Add 'PLATAFORMAS' value to category_enum PostgreSQL type
"""
from typing import Sequence, Union

from alembic import op

revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE category_enum ADD VALUE IF NOT EXISTS 'PLATAFORMAS'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    pass
