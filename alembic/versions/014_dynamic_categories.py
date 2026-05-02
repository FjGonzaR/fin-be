"""dynamic categories: enum -> table + keywords

Revision ID: 014
Revises: 013
Create Date: 2026-05-01

Changes:
- Create `categories` table (admin-managed list, replaces hardcoded enum)
- Create `category_keywords` table (rules engine seed + learned from reclassifications)
- Seed both from existing enum values + categorization.RULES dict
- Migrate `transactions.category` enum -> `transactions.category_id` FK
- Migrate `category_examples.category` enum -> `category_examples.category_id` FK
- Drop old enum columns and `category_enum` type
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (slug, display name, is_system)
SEED_CATEGORIES: list[tuple[str, str, bool]] = [
    ("HOGAR", "Hogar", False),
    ("DOMICILIOS", "Domicilios", False),
    ("CARRO", "Carro", False),
    ("TRANSPORTE", "Transporte", False),
    ("OCIO", "Ocio", False),
    ("RESTAURANTES", "Restaurantes", False),
    ("ROPA", "Ropa", False),
    ("SALUD", "Salud", False),
    ("PRESTACIONES", "Prestaciones", False),
    ("REGALOS", "Regalos", False),
    ("EDUCACION", "Educación", False),
    ("TRABAJO", "Trabajo", False),
    ("COBRO_BANCARIO", "Cobro bancario", False),
    ("PAGO", "Pago", True),
    ("PLATAFORMAS", "Plataformas", False),
    ("INGRESO", "Ingreso", True),
    ("INVERSION", "Inversión", True),
    ("MOVIMIENTO_ENTRE_BANCOS", "Movimiento entre bancos", True),
    ("OTROS", "Otros", True),
]

# slug -> [keywords] (mirrors app.etl.categorization.RULES at the time of migration)
SEED_KEYWORDS: dict[str, list[str]] = {
    "INGRESO": [
        "TRANSF DE", "TRANSFERENCIA DESDE NEQUI", "ABONO INTERESES AHORROS",
        "PAGO INTERBANC", "RECIBI POR BRE-B DE", "Pago de Intereses", "De ",
    ],
    "MOVIMIENTO_ENTRE_BANCOS": [
        "Recarga desde Bancolombia", "Recarga en:",
    ],
    "INVERSION": [
        "PAGO CORREVAL", "CORREVAL FIDUCIA",
        "PSE Credicorp Capital", "PAGO PSE Credicorp",
    ],
    "PAGO": [
        "ABONO SUCURSAL VIRTUAL", "PAGO SUC VIRT TC",
    ],
    "COBRO_BANCARIO": [
        "CUOTA DE MANEJO", "CUOTA MANEJO TRJ", "CUOTA MANEJO",
        "IMPTO GOBIERNO 4X1000", "4X1000",
        "COMISION BANCARIA", "COBRO BANCARIO",
    ],
    "DOMICILIOS": [
        "DLO*DIDI FOOD", "DIDI FOOD", "RAPPI",
    ],
    "CARRO": [
        "PARQUEADERO",
    ],
    "TRANSPORTE": [
        "DL DIDI RIDES", "DIDI RIDES", "DLO*DIDI", "UBER",
    ],
    "SALUD": [
        "FARMATODO", "DROGUERIA", "DROG", "IPS", "ACTION BLACK",
    ],
    "HOGAR": [
        "EXITO", "D1", "TIENDA D1", "HOMECENTER", "COMCEL",
        "PAGO FACTURA MOVIL", "TRANSF A ENEL", "TRANSF A VANTI",
    ],
    "RESTAURANTES": [
        "JUAN VALDEZ", "STARBUCKS", "IL FORNO", "PARMESSANO", "CAFE",
        "CREPESYWAFFLES", "HELADERIA", "DELIMEX", "SABORES NIKKEI",
        "MAESTRIA DEL FUEGO", "PASTIER", "BOLD*", "TJV", "GRUPO MURRI",
    ],
    "OCIO": [
        "CINECITY", "MIRANDA DISCO", "BAR Y GRILL",
        "APPARTA", "AEROREPUBLICA", "PRIORITY PASS",
        "FALABELLA", "AMAZON MKTPL", "PAYPAL", "MERCADOPAGO",
    ],
    "PLATAFORMAS": [
        "NETFLIX", "SPOTIFY", "APPLE.COM/BILL",
    ],
    "TRABAJO": [
        "OPENAI", "CHATGPT", "CLAUDE", "CURSOR", "OPENROUTER",
    ],
    "PRESTACIONES": [
        "PAGO CARDIF", "CARDIF",
    ],
}

KEYWORD_ORIGIN_VALUES = ("MANUAL", "LEARNED")


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Create keyword origin enum type
    origin_enum = PgEnum(*KEYWORD_ORIGIN_VALUES, name="keyword_origin_enum", create_type=True)
    origin_enum.create(bind, checkfirst=True)

    # 2. Create categories table
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"])

    # 3. Create category_keywords table
    origin_ref = PgEnum(*KEYWORD_ORIGIN_VALUES, name="keyword_origin_enum", create_type=False)
    op.create_table(
        "category_keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keyword", sa.Text(), nullable=False),
        sa.Column("origin", origin_ref, nullable=False, server_default="MANUAL"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("category_id", "keyword", name="uq_category_keyword"),
    )
    op.create_index("ix_category_keywords_keyword", "category_keywords", ["keyword"])

    # 4. Seed categories (generate UUIDs in Python — no pgcrypto dependency)
    categories_table = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.Text),
        sa.column("name", sa.Text),
        sa.column("is_system", sa.Boolean),
    )
    cat_rows = []
    slug_to_id: dict[str, uuid.UUID] = {}
    for slug, name, is_sys in SEED_CATEGORIES:
        cid = uuid.uuid4()
        slug_to_id[slug] = cid
        cat_rows.append({"id": cid, "slug": slug, "name": name, "is_system": is_sys})
    op.bulk_insert(categories_table, cat_rows)

    # 5. Seed manual keywords
    keyword_inserts = []
    for slug, kws in SEED_KEYWORDS.items():
        cat_id = slug_to_id.get(slug)
        if not cat_id:
            continue
        for kw in kws:
            keyword_inserts.append(
                {"id": uuid.uuid4(), "category_id": cat_id, "keyword": kw, "origin": "MANUAL"}
            )

    if keyword_inserts:
        keywords_table = sa.table(
            "category_keywords",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("category_id", postgresql.UUID(as_uuid=True)),
            sa.column("keyword", sa.Text),
            sa.column("origin", origin_ref),
        )
        op.bulk_insert(keywords_table, keyword_inserts)

    # 6. Add category_id to transactions and category_examples; backfill
    op.add_column(
        "transactions",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
    )
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])

    op.add_column(
        "category_examples",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=True),
    )

    # Backfill: cast enum to text and join on slug
    op.execute(
        """
        UPDATE transactions t
        SET category_id = c.id
        FROM categories c
        WHERE c.slug = t.category::text
        """
    )
    op.execute(
        """
        UPDATE category_examples e
        SET category_id = c.id
        FROM categories c
        WHERE c.slug = e.category::text
        """
    )

    # 7. Drop old enum columns + unique constraint that referenced category enum
    op.drop_constraint("uq_category_examples_desc_cat", "category_examples", type_="unique")
    op.drop_column("transactions", "category")
    op.drop_column("category_examples", "category")

    # Recreate unique constraint with new FK
    op.create_unique_constraint(
        "uq_category_examples_desc_cat",
        "category_examples",
        ["description_clean", "category_id"],
    )

    # category_examples.category_id must be NOT NULL going forward
    op.alter_column("category_examples", "category_id", nullable=False)

    # 8. Drop the old category_enum type
    PgEnum(name="category_enum").drop(bind, checkfirst=True)


def downgrade() -> None:
    # Recreate category_enum from current category slugs
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT slug FROM categories ORDER BY slug")).fetchall()
    slugs = tuple(r.slug for r in rows) or ("OTROS",)

    cat_enum = PgEnum(*slugs, name="category_enum", create_type=True)
    cat_enum.create(bind, checkfirst=True)
    cat_ref = PgEnum(*slugs, name="category_enum", create_type=False)

    # Restore enum columns (nullable, then backfill)
    op.drop_constraint("uq_category_examples_desc_cat", "category_examples", type_="unique")

    op.add_column("transactions", sa.Column("category", cat_ref, nullable=True))
    op.add_column("category_examples", sa.Column("category", cat_ref, nullable=True))

    op.execute(
        """
        UPDATE transactions t
        SET category = c.slug::category_enum
        FROM categories c
        WHERE c.id = t.category_id
        """
    )
    op.execute(
        """
        UPDATE category_examples e
        SET category = c.slug::category_enum
        FROM categories c
        WHERE c.id = e.category_id
        """
    )

    op.create_unique_constraint(
        "uq_category_examples_desc_cat",
        "category_examples",
        ["description_clean", "category"],
    )
    op.alter_column("category_examples", "category", nullable=False)

    op.drop_index("ix_transactions_category_id", table_name="transactions")
    op.drop_column("transactions", "category_id")
    op.drop_column("category_examples", "category_id")

    op.drop_index("ix_category_keywords_keyword", table_name="category_keywords")
    op.drop_table("category_keywords")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")

    PgEnum(name="keyword_origin_enum").drop(bind, checkfirst=True)
