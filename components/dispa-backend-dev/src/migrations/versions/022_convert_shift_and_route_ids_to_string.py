"""Convert shift_tasks and route_tasks IDs back to String

Revision ID: 022
Revises: 021
Create Date: 2026-03-16

Меняет типы колонок:
1. shift_tasks.id: UUID -> VARCHAR(50)
2. route_tasks.id: UUID -> VARCHAR(50)
3. route_tasks.shift_task_id: UUID -> VARCHAR(50)

Предполагается, что все значения UUID можно безопасно привести к строкам.
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Миграция вверх:
    1. Удалить внешний ключ route_tasks_shift_task_id_fkey
    2. Конвертировать route_tasks.shift_task_id из UUID в VARCHAR(50)
    3. Конвертировать route_tasks.id из UUID в VARCHAR(50)
    4. Конвертировать shift_tasks.id из UUID в VARCHAR(50)
    5. Восстановить внешний ключ
    """

    # 1. Удаляем внешний ключ
    op.drop_constraint(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        type_="foreignkey",
    )

    # 2. Конвертируем route_tasks.shift_task_id обратно в строку
    op.alter_column(
        "route_tasks",
        "shift_task_id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="shift_task_id::text",
    )

    # 3. Конвертируем route_tasks.id обратно в строку
    op.alter_column(
        "route_tasks",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="id::text",
    )

    # 4. Конвертируем shift_tasks.id обратно в строку
    op.alter_column(
        "shift_tasks",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="id::text",
    )

    # 5. Восстанавливаем внешний ключ
    op.create_foreign_key(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        "shift_tasks",
        ["shift_task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """
    Откат миграции:
    1. Удалить внешний ключ route_tasks_shift_task_id_fkey
    2. Конвертировать shift_tasks.id из VARCHAR(50) в UUID
    3. Конвертировать route_tasks.id из VARCHAR(50) в UUID
    4. Конвертировать route_tasks.shift_task_id из VARCHAR(50) в UUID
    5. Восстановить внешний ключ
    """

    # 1. Удаляем внешний ключ
    op.drop_constraint(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        type_="foreignkey",
    )

    # 2. Конвертируем shift_tasks.id обратно в UUID
    op.alter_column(
        "shift_tasks",
        "id",
        existing_type=sa.String(length=50),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="id::uuid",
    )

    # 3. Конвертируем route_tasks.id обратно в UUID
    op.alter_column(
        "route_tasks",
        "id",
        existing_type=sa.String(length=50),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="id::uuid",
    )

    # 4. Конвертируем route_tasks.shift_task_id обратно в UUID
    op.alter_column(
        "route_tasks",
        "shift_task_id",
        existing_type=sa.String(length=50),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="shift_task_id::uuid",
    )

    # 5. Восстанавливаем внешний ключ
    op.create_foreign_key(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        "shift_tasks",
        ["shift_task_id"],
        ["id"],
        ondelete="CASCADE",
    )

