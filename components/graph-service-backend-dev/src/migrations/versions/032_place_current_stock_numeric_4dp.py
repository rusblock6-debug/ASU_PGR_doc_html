"""Store place.current_stock with 4 decimal places.

Revision ID: 032
Revises: 031
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def _table_has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    cols = {c["name"] for c in inspector.get_columns(table)}
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    target_type = sa.Numeric(20, 4)

    for table in ("place_load", "place_unload", "place_reload"):
        if not _table_has_column(inspector, table, "current_stock"):
            continue
        op.alter_column(
            table,
            "current_stock",
            type_=target_type,
            existing_type=sa.Float(),
            postgresql_using="current_stock::numeric(20,4)",
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table in ("place_load", "place_unload", "place_reload"):
        if not _table_has_column(inspector, table, "current_stock"):
            continue
        op.alter_column(
            table,
            "current_stock",
            type_=sa.Float(),
            existing_type=sa.Numeric(20, 4),
            postgresql_using="current_stock::double precision",
        )

