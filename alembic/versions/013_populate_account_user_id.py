"""populate account user_id from owner label

Revision ID: 013
Revises: 012
Create Date: 2026-04-09

Changes:
- Map existing accounts to users by case-insensitive username match on owner label
  e.g. account.owner='PACHO' → user with username='pacho' (or 'PACHO', any case)
- Accounts with no matching user are left with user_id=NULL (admin assigns manually)
"""
from typing import Sequence, Union

from alembic import op

revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    total = conn.exec_driver_sql(
        "SELECT COUNT(*) FROM accounts WHERE user_id IS NULL"
    ).scalar()

    op.execute("""
        UPDATE accounts a
        SET user_id = u.id
        FROM users u
        WHERE lower(u.username) = lower(a.owner)
          AND a.user_id IS NULL
    """)

    unassigned = conn.exec_driver_sql(
        "SELECT COUNT(*) FROM accounts WHERE user_id IS NULL"
    ).scalar()

    if unassigned:
        print(
            f"\n[migration 013] WARNING: {unassigned}/{total} accounts have no matching user "
            f"and were left with user_id=NULL. "
            f"Use GET /admin/accounts/unassigned to assign them after deploy."
        )
    else:
        print(f"\n[migration 013] All {total} accounts successfully assigned to users.")


def downgrade() -> None:
    # Reverse: clear user_id (owner label is still present, so data is not lost)
    op.execute("UPDATE accounts SET user_id = NULL")
