"""
Remove bort_id and legacy vehicle columns no longer used in models.

Revision ID: 008_remove_bort_and_legacy_vehicle_columns
Revises: 007_refactor_status_model
Create Date: 2025-12-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


LEGACY_COLUMNS = [
    ("bort_id", sa.String(length=100), {"nullable": False, "server_default": "4_truck"}),
    ("model", sa.String(length=100), {"nullable": True}),
    ("engine_power_hp", sa.Integer(), {"nullable": True}),
    ("tank_volume", sa.Float(), {"nullable": True}),
    ("capacity_tons", sa.Float(), {"nullable": True}),
    ("bucket_volume_m3", sa.Float(), {"nullable": True}),
    ("payload_tons", sa.Float(), {"nullable": True}),
    ("dump_body_volume_m3", sa.Float(), {"nullable": True}),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("vehicles")}

    for column_name, _, _ in LEGACY_COLUMNS:
        if column_name in columns:
            op.drop_column("vehicles", column_name)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("vehicles")}

    for column_name, column_type, params in LEGACY_COLUMNS:
        if column_name not in columns:
            op.add_column(
                "vehicles",
                sa.Column(column_name, column_type, **params),
            )

