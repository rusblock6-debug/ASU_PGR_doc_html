"""Make place start_date not null for all operational subtypes.

Revision ID: 030
Revises: 029
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    for table_name in ("place_load", "place_unload", "place_reload"):
        if table_name not in tables:
            continue

        columns = {c["name"]: c for c in inspector.get_columns(table_name)}
        if "start_date" not in columns:
            continue

        # Defensive backfill: existing NULL values would block NOT NULL constraint.
        op.execute(
            sa.text(
                f"UPDATE {table_name} SET start_date = CURRENT_DATE WHERE start_date IS NULL",
            ),
        )

        op.alter_column(
            table_name,
            "start_date",
            existing_type=sa.Date(),
            nullable=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    for table_name in ("place_load", "place_unload", "place_reload"):
        if table_name not in tables:
            continue

        columns = {c["name"] for c in inspector.get_columns(table_name)}
        if "start_date" not in columns:
            continue

        op.alter_column(
            table_name,
            "start_date",
            existing_type=sa.Date(),
            nullable=True,
        )

