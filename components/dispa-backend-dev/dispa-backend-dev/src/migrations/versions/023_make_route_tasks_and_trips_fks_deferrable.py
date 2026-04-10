"""Make route_tasks and trips foreign keys deferrable

Revision ID: 023
Revises: 022
Create Date: 2026-04-01

Пересоздаёт внешние ключи с DEFERRABLE (как в app.database.models.ForeignKey(..., deferrable=True)).
"""

from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        "shift_tasks",
        ["shift_task_id"],
        ["id"],
        ondelete="CASCADE",
        deferrable=True,
    )

    op.drop_constraint(
        "trips_cycle_id_fkey",
        "trips",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "trips_cycle_id_fkey",
        "trips",
        "cycles",
        ["cycle_id"],
        ["cycle_id"],
        deferrable=True,
    )


def downgrade() -> None:
    op.drop_constraint(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        "shift_tasks",
        ["shift_task_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "trips_cycle_id_fkey",
        "trips",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "trips_cycle_id_fkey",
        "trips",
        "cycles",
        ["cycle_id"],
        ["cycle_id"],
    )
