"""Add operator staff_id to shift_tasks

Revision ID: 026
Revises: 025
Create Date: 2026-04-10
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shift_tasks",
        sa.Column("staff_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_shift_tasks_staff_id", "shift_tasks", ["staff_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_shift_tasks_staff_id", table_name="shift_tasks")
    op.drop_column("shift_tasks", "staff_id")
