"""add seq_id to bort_stream_offsets

Revision ID: 002
Revises: 001
Create Date: 2026-03-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002'
down_revision: Union[str, Sequence[str], None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bort_stream_offsets",
        sa.Column("seq_id", sa.BigInteger, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("bort_stream_offsets", "seq_id")
