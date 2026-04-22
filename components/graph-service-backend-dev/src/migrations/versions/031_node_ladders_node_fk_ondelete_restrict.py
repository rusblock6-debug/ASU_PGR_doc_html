"""Set ON DELETE RESTRICT for node_ladders.node_id FK.

Revision ID: 031
Revises: 030
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def _get_fk_name(inspector: sa.Inspector, table: str, referred_table: str, constrained_columns: list[str]) -> str | None:
    for fk in inspector.get_foreign_keys(table):
        if fk.get("referred_table") != referred_table:
            continue
        if list(fk.get("constrained_columns") or []) != constrained_columns:
            continue
        return fk.get("name")
    return None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = set(inspector.get_table_names())
    if "node_ladders" not in tables:
        return

    fk_name = _get_fk_name(inspector, "node_ladders", "graph_nodes", ["node_id"])
    if fk_name:
        op.drop_constraint(fk_name, "node_ladders", type_="foreignkey")

    op.create_foreign_key(
        "fk_node_ladders_node_id_graph_nodes",
        "node_ladders",
        "graph_nodes",
        ["node_id"],
        ["id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="IMMEDIATE",
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = set(inspector.get_table_names())
    if "node_ladders" not in tables:
        return

    # Drop our FK if present
    op.execute(sa.text("ALTER TABLE node_ladders DROP CONSTRAINT IF EXISTS fk_node_ladders_node_id_graph_nodes"))

    # Restore prior behaviour (no explicit ON DELETE)
    op.create_foreign_key(
        "fk_node_ladders_node_id_graph_nodes",
        "node_ladders",
        "graph_nodes",
        ["node_id"],
        ["id"],
        deferrable=True,
        initially="IMMEDIATE",
    )

