"""Convert shift_tasks and route_tasks IDs to UUID

Revision ID: 013
Revises: 012
Create Date: 2026-01-27

Конвертирует:
1. shift_tasks.id: VARCHAR(255) -> UUID
2. route_tasks.id: VARCHAR(255) -> UUID
3. route_tasks.shift_task_id: VARCHAR(255) -> UUID

Предполагается, что все существующие значения уже являются валидными UUID строками (32 символа).
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Миграция вверх:
    1. Удалить внешний ключ route_tasks_shift_task_id_fkey
    2. Конвертировать shift_tasks.id из VARCHAR(255) в UUID
    3. Конвертировать route_tasks.id из VARCHAR(255) в UUID
    4. Конвертировать route_tasks.shift_task_id из VARCHAR(255) в UUID
    5. Восстановить внешний ключ
    """
    
    # ============================================
    # 1. Удалить внешний ключ (иначе нельзя изменить тип)
    # ============================================
    op.drop_constraint(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        type_="foreignkey"
    )
    
    # ============================================
    # 2. Конвертировать shift_tasks.id
    # ============================================
    op.alter_column(
        "shift_tasks",
        "id",
        existing_type=sa.String(length=255),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="id::uuid",
    )
    
    # ============================================
    # 3. Конвертировать route_tasks.id
    # ============================================
    op.alter_column(
        "route_tasks",
        "id",
        existing_type=sa.String(length=255),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="id::uuid",
    )
    
    # ============================================
    # 4. Конвертировать route_tasks.shift_task_id
    # ============================================
    op.alter_column(
        "route_tasks",
        "shift_task_id",
        existing_type=sa.String(length=255),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using="shift_task_id::uuid",
    )
    
    # ============================================
    # 5. Восстановить внешний ключ
    # ============================================
    op.create_foreign_key(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        "shift_tasks",
        ["shift_task_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    """
    Откат миграции:
    1. Удалить внешний ключ route_tasks_shift_task_id_fkey
    2. Конвертировать route_tasks.shift_task_id из UUID в VARCHAR(255)
    3. Конвертировать route_tasks.id из UUID в VARCHAR(255)
    4. Конвертировать shift_tasks.id из UUID в VARCHAR(255)
    5. Восстановить внешний ключ
    """
    
    # ============================================
    # 1. Удалить внешний ключ
    # ============================================
    op.drop_constraint(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        type_="foreignkey"
    )
    
    # ============================================
    # 2. Конвертировать route_tasks.shift_task_id обратно
    # ============================================
    op.alter_column(
        "route_tasks",
        "shift_task_id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(length=255),
        existing_nullable=False,
        postgresql_using="shift_task_id::text",
    )
    
    # ============================================
    # 3. Конвертировать route_tasks.id обратно
    # ============================================
    op.alter_column(
        "route_tasks",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(length=255),
        existing_nullable=False,
        postgresql_using="id::text",
    )
    
    # ============================================
    # 4. Конвертировать shift_tasks.id обратно
    # ============================================
    op.alter_column(
        "shift_tasks",
        "id",
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.String(length=255),
        existing_nullable=False,
        postgresql_using="id::text",
    )
    
    # ============================================
    # 5. Восстановить внешний ключ
    # ============================================
    op.create_foreign_key(
        "route_tasks_shift_task_id_fkey",
        "route_tasks",
        "shift_tasks",
        ["shift_task_id"],
        ["id"],
        ondelete="CASCADE"
    )
