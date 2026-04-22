"""Update place_remaining_history: volume/weight and load_type

Revision ID: 024
Revises: 023
Create Date: 2026-04-02

Changes:
- rename column change_amount -> change_volume
- add columns load_type_id (int, nullable) and change_weight (float, nullable)
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels = None
depends_on = None

_TABLE = "place_remaining_history"


def upgrade() -> None:
    op.alter_column(
        _TABLE,
        "change_amount",
        new_column_name="change_volume",
        existing_type=sa.Float(),
        existing_nullable=False,
    )

    op.add_column(_TABLE, sa.Column("load_type_id", sa.Integer(), nullable=True))
    op.add_column(_TABLE, sa.Column("change_weight", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column(_TABLE, "change_weight")
    op.drop_column(_TABLE, "load_type_id")

    op.alter_column(
        _TABLE,
        "change_volume",
        new_column_name="change_amount",
        existing_type=sa.Float(),
        existing_nullable=False,
    )

