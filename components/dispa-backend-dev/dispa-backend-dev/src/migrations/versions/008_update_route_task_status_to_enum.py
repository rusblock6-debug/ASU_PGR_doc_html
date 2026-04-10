"""Update route_tasks status values

Revision ID: 008
Revises: 007
Create Date: 2025-12-08

Обновляет значения статусов route_tasks (колонка остается VARCHAR).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Обновление значений статуса route_tasks (колонка остается VARCHAR).
    1. Обновляем существующие данные (маппинг старых значений)
    2. Обновляем DEFAULT
    """
    
    # 1. Обновляем существующие данные
    op.execute("""
        UPDATE route_tasks 
        SET status = 'delivered' 
        WHERE status = 'pending'
    """)
    
    op.execute("""
        UPDATE route_tasks 
        SET status = 'rejected' 
        WHERE status = 'cancelled'
    """)
    
    # "paused" остается "paused" - без изменений
    
    # 2. Обновляем DEFAULT (колонка остается VARCHAR)
    op.execute("ALTER TABLE route_tasks ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE route_tasks ALTER COLUMN status SET DEFAULT 'delivered'")


def downgrade() -> None:
    """
    Откат: восстановление старых значений и DEFAULT
    """
    
    # 1. Откатываем изменения данных (обратный маппинг)
    op.execute("""
        UPDATE route_tasks 
        SET status = 'pending' 
        WHERE status = 'delivered'
    """)
    
    op.execute("""
        UPDATE route_tasks 
        SET status = 'cancelled' 
        WHERE status = 'rejected'
    """)
    
    # 2. Восстанавливаем старый DEFAULT
    op.execute("ALTER TABLE route_tasks ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE route_tasks ALTER COLUMN status SET DEFAULT 'pending'")

