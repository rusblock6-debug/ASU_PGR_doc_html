"""Allow nullable place_id and change_volume in place_remaining_history.

Revision ID: 025
Revises: 024
Create Date: 2026-04-02

Changes:
- make place_remaining_history.place_id nullable
- make place_remaining_history.change_volume nullable
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "place_remaining_history",
        "change_volume",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "place_remaining_history",
        "place_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "place_remaining_history",
        "change_volume",
        existing_type=sa.Float(),
        nullable=False,
    )
