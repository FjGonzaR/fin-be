"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bank_name', sa.Text(), nullable=False),
        sa.Column('account_name', sa.Text(), nullable=False),
        sa.Column('currency', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    )

    # Create source_files table
    op.create_table(
        'source_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bank_name', sa.Text(), nullable=False),
        sa.Column('file_type', sa.Text(), nullable=False),
        sa.Column('uploaded_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('file_hash', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.Text(), nullable=False),
        sa.Column('storage_uri', sa.Text(), nullable=False),
        sa.Column('parse_status', sa.Text(), nullable=False),
    )
    op.create_unique_constraint('uq_source_files_file_hash', 'source_files', ['file_hash'])

    # Create raw_rows table
    op.create_table(
        'raw_rows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('raw_data_json', postgresql.JSONB(), nullable=False),
        sa.Column('parse_warnings', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['source_file_id'], ['source_files.id']),
    )

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('posted_at', sa.Date(), nullable=False),
        sa.Column('description_raw', sa.Text(), nullable=False),
        sa.Column('description_clean', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.Text(), nullable=False),
        sa.Column('merchant_guess', sa.Text(), nullable=True),
        sa.Column('fingerprint', sa.Text(), nullable=False),
        sa.Column('details_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['source_file_id'], ['source_files.id']),
    )
    op.create_unique_constraint('uq_transactions_fingerprint', 'transactions', ['fingerprint'])
    op.create_index('ix_transactions_account_posted', 'transactions', ['account_id', 'posted_at'])
    op.create_index('ix_transactions_posted', 'transactions', ['posted_at'])


def downgrade() -> None:
    op.drop_index('ix_transactions_posted', table_name='transactions')
    op.drop_index('ix_transactions_account_posted', table_name='transactions')
    op.drop_table('transactions')
    op.drop_table('raw_rows')
    op.drop_table('source_files')
    op.drop_table('accounts')
