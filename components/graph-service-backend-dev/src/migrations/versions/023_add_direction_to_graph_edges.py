"""Add direction field to graph_edges.

Revision ID: 023
Revises: 022
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "graph_edges" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("graph_edges")}
    if "direction" not in columns:
        op.add_column(
            "graph_edges",
            sa.Column(
                "direction",
                sa.String(length=32),
                nullable=False,
                server_default="Двунаправленное",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "graph_edges" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("graph_edges")}
    if "direction" in columns:
        op.drop_column("graph_edges", "direction")

