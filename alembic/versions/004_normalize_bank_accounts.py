"""normalize bank accounts

Revision ID: 004
Revises: 003
Create Date: 2026-03-06

Changes:
- Add bank_enum PostgreSQL type (BANCOLOMBIA, RAPPI)
- Add account_id FK to source_files (bank moves to account level)
- Drop bank_name from source_files
- Convert accounts.bank_name from Text to bank_enum
- Drop account_id from transactions (derived via source_file → account)
- Drop ix_transactions_account_posted composite index
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create bank_enum PostgreSQL type
    op.execute("CREATE TYPE bank_enum AS ENUM ('BANCOLOMBIA', 'RAPPI')")

    # Step 2: Add account_id to source_files (nullable initially for data migration)
    op.add_column(
        'source_files',
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_source_files_account_id',
        'source_files', 'accounts',
        ['account_id'], ['id'],
    )

    # Step 3: Populate source_files.account_id from existing transactions
    # (most source_files already have transactions pointing to their account)
    op.execute("""
        UPDATE source_files sf
        SET account_id = sub.account_id
        FROM (
            SELECT DISTINCT ON (source_file_id) source_file_id, account_id
            FROM transactions
            ORDER BY source_file_id
        ) sub
        WHERE sf.id = sub.source_file_id
          AND sf.account_id IS NULL
    """)

    # Step 4: For source_files still without account_id, match by bank_name similarity
    # (handles source_files that have no transactions yet)
    op.execute("""
        UPDATE source_files sf
        SET account_id = (
            SELECT a.id
            FROM accounts a
            WHERE
                (LOWER(a.bank_name) LIKE '%rappi%') = (LOWER(sf.bank_name) LIKE '%rappi%')
            LIMIT 1
        )
        WHERE sf.account_id IS NULL
    """)

    # Step 5: Convert accounts.bank_name from Text to bank_enum
    op.execute("""
        ALTER TABLE accounts
        ALTER COLUMN bank_name TYPE bank_enum
        USING CASE
            WHEN LOWER(bank_name) LIKE '%rappi%' THEN 'RAPPI'::bank_enum
            ELSE 'BANCOLOMBIA'::bank_enum
        END
    """)

    # Step 6: Drop bank_name from source_files
    op.drop_column('source_files', 'bank_name')

    # Step 7: Drop account_id from transactions (+ its FK and composite index)
    op.drop_index('ix_transactions_account_posted', table_name='transactions')
    op.drop_constraint('transactions_account_id_fkey', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'account_id')


def downgrade() -> None:
    # Re-add account_id to transactions
    op.add_column(
        'transactions',
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'transactions_account_id_fkey',
        'transactions', 'accounts',
        ['account_id'], ['id'],
    )
    # Restore account_id from source_files
    op.execute("""
        UPDATE transactions t
        SET account_id = sf.account_id
        FROM source_files sf
        WHERE t.source_file_id = sf.id
    """)
    op.alter_column('transactions', 'account_id', nullable=False)
    op.create_index('ix_transactions_account_posted', 'transactions', ['account_id', 'posted_at'])

    # Re-add bank_name to source_files
    op.add_column('source_files', sa.Column('bank_name', sa.Text(), nullable=True))
    op.execute("""
        UPDATE source_files sf
        SET bank_name = a.bank_name::text
        FROM accounts a
        WHERE sf.account_id = a.id
    """)
    op.alter_column('source_files', 'bank_name', nullable=False)

    # Revert accounts.bank_name back to Text
    op.execute("""
        ALTER TABLE accounts
        ALTER COLUMN bank_name TYPE text
        USING bank_name::text
    """)

    # Drop FK and account_id from source_files
    op.drop_constraint('fk_source_files_account_id', 'source_files', type_='foreignkey')
    op.drop_column('source_files', 'account_id')

    # Drop bank_enum type
    op.execute("DROP TYPE bank_enum")
