"""create bort_stream_offsets

Revision ID: 001
Revises:
Create Date: 2026-03-26 17:00:29.048805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bort_stream_offsets",
        sa.Column("stream_name", sa.String(255), nullable=False),
        sa.Column("bort_id", sa.Integer, nullable=False),
        sa.Column("offset_value", sa.BigInteger, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("stream_name", "bort_id"),
    )


def downgrade() -> None:
    op.drop_table("bort_stream_offsets")
