"""add categorization

Revision ID: 002
Revises: 001
Create Date: 2026-03-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORY_VALUES = (
    "HOGAR", "DOMICILIOS", "CARRO", "TRANSPORTE", "OCIO", "RESTAURANTES",
    "ROPA", "SALUD", "PRESTACIONES", "REGALOS", "EDUCACION", "TRABAJO",
    "COBRO_BANCARIO", "PAGO", "OTROS",
)
CATEGORY_METHOD_VALUES = ("RULES", "LLM", "USER")


def upgrade() -> None:
    category_enum = PgEnum(*CATEGORY_VALUES, name="category_enum", create_type=True)
    category_method_enum = PgEnum(*CATEGORY_METHOD_VALUES, name="category_method_enum", create_type=True)

    category_enum.create(op.get_bind(), checkfirst=True)
    category_method_enum.create(op.get_bind(), checkfirst=True)

    # Reference types without re-creating them
    cat_ref = PgEnum(*CATEGORY_VALUES, name="category_enum", create_type=False)
    cat_method_ref = PgEnum(*CATEGORY_METHOD_VALUES, name="category_method_enum", create_type=False)

    op.add_column("transactions", sa.Column("category", cat_ref, nullable=True))
    op.add_column("transactions", sa.Column("category_confidence", sa.Numeric(3, 2), nullable=True))
    op.add_column("transactions", sa.Column("category_method", cat_method_ref, nullable=True))

    op.create_table(
        "category_examples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("description_clean", sa.Text(), nullable=False),
        sa.Column("category", PgEnum(*CATEGORY_VALUES, name="category_enum", create_type=False), nullable=False),
        sa.Column("merchant", sa.Text(), nullable=True),
        sa.Column("amount_sign", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_category_examples_desc_cat",
        "category_examples",
        ["description_clean", "category"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_category_examples_desc_cat", "category_examples", type_="unique")
    op.drop_table("category_examples")
    op.drop_column("transactions", "category_method")
    op.drop_column("transactions", "category_confidence")
    op.drop_column("transactions", "category")
    PgEnum(name="category_method_enum").drop(op.get_bind(), checkfirst=True)
    PgEnum(name="category_enum").drop(op.get_bind(), checkfirst=True)
