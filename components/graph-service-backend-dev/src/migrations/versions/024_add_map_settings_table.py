"""Add map_settings table.

Revision ID: 024
Revises: 023
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "map_settings" in tables:
        return

    op.create_table(
        "map_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("RoutesColor", sa.String(length=7), nullable=False, server_default="#6A848B"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "map_settings" not in tables:
        return

    op.drop_table("map_settings")


