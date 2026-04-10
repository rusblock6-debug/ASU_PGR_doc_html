"""Create dispatcher_assignments table for dispatcher route/garage assignments

Revision ID: 021
Revises: 020
Create Date: 2026-03-05

Таблица dispatcher_assignments хранит назначения диспетчером:
- откуда техника «логически» перемещается (маршрут / нет задания / гараж)
- куда она должна быть перемещена (маршрут или конкретный гараж)
Назначение живёт в статусе pending до ответа борта (approved / rejected).
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
  """Создать таблицу dispatcher_assignments."""
  op.create_table(
      "dispatcher_assignments",
      sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
      sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
      sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
      sa.Column("vehicle_id", sa.Integer(), nullable=False),
      sa.Column("shift_date", sa.String(length=50), nullable=False),
      sa.Column("shift_num", sa.Integer(), nullable=False),
      sa.Column("source_kind", sa.String(length=20), nullable=False, comment="ROUTE | NO_TASK | GARAGE"),
      sa.Column("source_route_place_a_id", sa.Integer(), nullable=True),
      sa.Column("source_route_place_b_id", sa.Integer(), nullable=True),
      sa.Column("source_garage_place_id", sa.Integer(), nullable=True),
      sa.Column("target_kind", sa.String(length=20), nullable=False, comment="ROUTE | GARAGE"),
      sa.Column("target_route_place_a_id", sa.Integer(), nullable=True),
      sa.Column("target_route_place_b_id", sa.Integer(), nullable=True),
      sa.Column("target_garage_place_id", sa.Integer(), nullable=True),
      sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
  )

  op.create_index(
      "ix_dispatcher_assignments_vehicle_shift",
      "dispatcher_assignments",
      ["vehicle_id", "shift_date", "shift_num"],
  )


def downgrade() -> None:
  """Удалить таблицу dispatcher_assignments."""
  op.drop_index(
      "ix_dispatcher_assignments_vehicle_shift",
      table_name="dispatcher_assignments",
  )
  op.drop_table("dispatcher_assignments")

