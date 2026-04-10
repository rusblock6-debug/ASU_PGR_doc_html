"""add places table

Revision ID: 004
Revises: 003
Create Date: 2025-11-12 00:15:24.330042
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("location", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("available_vehicle_types", sa.String(length=50), nullable=True),
        sa.Column("capacity", sa.Float(), nullable=True),
        sa.Column("active_from", sa.Date(), nullable=True),
        sa.Column("active_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("primary_remainder", sa.Float(), nullable=True),
        sa.Column("tag_point_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tag_point_id"], ["tags.point_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_places_tag_point_id"), "places", ["tag_point_id"], unique=False)
    op.add_column("tags", sa.Column("mac_address", sa.String(length=17), nullable=True))


def downgrade() -> None:
    op.drop_column("tags", "mac_address")
    op.drop_index(op.f("ix_places_tag_point_id"), table_name="places")
    op.drop_table("places")