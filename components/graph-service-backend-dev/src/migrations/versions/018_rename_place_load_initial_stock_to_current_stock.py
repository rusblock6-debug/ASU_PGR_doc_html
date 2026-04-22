"""Rename place_load.initial_stock to current_stock

Revision ID: 018
Revises: 017
Create Date: 2026-01-21
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Defensive: only rename if table/column exists (idempotent-ish for mixed envs)
    if "place_load" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("place_load")}
    if "initial_stock" in cols and "current_stock" not in cols:
        op.alter_column("place_load", "initial_stock", new_column_name="current_stock")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "place_load" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("place_load")}
    if "current_stock" in cols and "initial_stock" not in cols:
        op.alter_column("place_load", "current_stock", new_column_name="initial_stock")


