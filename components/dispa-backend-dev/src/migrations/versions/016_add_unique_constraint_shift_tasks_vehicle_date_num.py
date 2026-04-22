"""Add unique constraint on shift_tasks (vehicle_id, shift_date, shift_num)

Revision ID: 016
Revises: 015
Create Date: 2026-01-27

Добавляет уникальное ограничение на комбинацию полей:
- vehicle_id
- shift_date
- shift_num

Это гарантирует, что для одного транспортного средства не может быть
двух смен с одинаковой датой и номером смены.
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Миграция вверх: обработка дубликатов и создание уникального ограничения.
    
    Шаги:
    1. Найти все дубликаты по (vehicle_id, shift_date, shift_num)
    2. Удалить дубликаты, оставив только самую новую запись (по created_at)
    3. Создать уникальное ограничение
    """
    # 1. Удаляем дубликаты, оставляя только самую новую запись для каждой комбинации
    # Используем DELETE с подзапросом для удаления всех записей, кроме самой новой
    op.execute("""
        DELETE FROM shift_tasks
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY vehicle_id, shift_date, shift_num 
                           ORDER BY created_at DESC
                       ) as rn
                FROM shift_tasks
            ) t
            WHERE rn > 1
        )
    """)
    
    # 2. Создаем уникальное ограничение
    op.create_unique_constraint(
        "uq_shift_tasks_vehicle_date_num",
        "shift_tasks",
        ["vehicle_id", "shift_date", "shift_num"]
    )


def downgrade() -> None:
    """
    Откат миграции: удаление уникального ограничения.
    """
    op.drop_constraint(
        "uq_shift_tasks_vehicle_date_num",
        "shift_tasks",
        type_="unique"
    )
