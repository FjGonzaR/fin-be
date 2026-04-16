"""add user roles and invitations

Revision ID: 012
Revises: 011
Create Date: 2026-04-09

Changes:
- Add is_admin and invited_by_id to users
- Add user_id FK to accounts
- Convert accounts.owner from owner_enum to TEXT (preserves existing values)
- Drop owner_enum type
- Create invitations table
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_admin to users
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))

    # 2. Add invited_by_id self-referential FK to users (nullable)
    op.add_column('users', sa.Column(
        'invited_by_id', postgresql.UUID(as_uuid=True), nullable=True
    ))
    op.create_foreign_key(
        'fk_users_invited_by',
        'users', 'users',
        ['invited_by_id'], ['id'],
        ondelete='SET NULL',
    )

    # 3. Add user_id FK to accounts (nullable — populated in migration 013)
    op.add_column('accounts', sa.Column(
        'user_id', postgresql.UUID(as_uuid=True), nullable=True
    ))
    op.create_foreign_key(
        'fk_accounts_user',
        'accounts', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL',
    )

    # 4. Convert accounts.owner from owner_enum to TEXT (values preserved as-is)
    op.execute("ALTER TABLE accounts ALTER COLUMN owner TYPE TEXT USING owner::text")

    # 5. Drop owner_enum type (now unused)
    op.execute("DROP TYPE owner_enum")

    # 6. Create invitations table
    op.create_table(
        'invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('token', sa.Text(), nullable=False, unique=True),
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_invitations_token', 'invitations', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_invitations_token', table_name='invitations')
    op.drop_table('invitations')

    op.drop_constraint('fk_accounts_user', 'accounts', type_='foreignkey')
    op.drop_column('accounts', 'user_id')

    # Restore owner_enum and convert TEXT column back to enum
    op.execute("CREATE TYPE owner_enum AS ENUM ('PACHO', 'LU')")
    op.execute("ALTER TABLE accounts ALTER COLUMN owner TYPE owner_enum USING owner::owner_enum")

    op.drop_constraint('fk_users_invited_by', 'users', type_='foreignkey')
    op.drop_column('users', 'invited_by_id')
    op.drop_column('users', 'is_admin')
