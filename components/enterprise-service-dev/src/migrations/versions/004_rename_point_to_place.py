"""
Переименование point_a_id/point_b_id в place_a_id/place_b_id и изменение типа на INTEGER.

Revision ID: 004
Revises: 003
Create Date: 2025-01-01

Изменения:
- route_tasks.point_a_id (VARCHAR) -> place_a_id (INTEGER)
- route_tasks.point_b_id (VARCHAR) -> place_b_id (INTEGER)
"""

from alembic import op
import sqlalchemy as sa
from loguru import logger


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Миграция вверх: переименование полей и изменение типа на INTEGER."""
    # Удаляем старые индексы если есть (используем IF EXISTS)
    op.execute("DROP INDEX IF EXISTS idx_route_tasks_point_a")
    op.execute("DROP INDEX IF EXISTS idx_route_tasks_point_b")
    
    # Добавляем новые колонки place_a_id и place_b_id (INTEGER)
    op.execute("""
        ALTER TABLE route_tasks 
        ADD COLUMN IF NOT EXISTS place_a_id INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE route_tasks 
        ADD COLUMN IF NOT EXISTS place_b_id INTEGER NOT NULL DEFAULT 0
    """)
    
    # Убираем default после создания колонок
    op.execute("""
        ALTER TABLE route_tasks 
        ALTER COLUMN place_a_id DROP DEFAULT
    """)
    op.execute("""
        ALTER TABLE route_tasks 
        ALTER COLUMN place_b_id DROP DEFAULT
    """)
    
    # Удаляем старые колонки point_a_id и point_b_id
    op.execute("ALTER TABLE route_tasks DROP COLUMN IF EXISTS point_a_id")
    op.execute("ALTER TABLE route_tasks DROP COLUMN IF EXISTS point_b_id")
    
    # Создаем новые индексы
    op.execute("CREATE INDEX IF NOT EXISTS idx_route_tasks_place_a ON route_tasks (place_a_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_route_tasks_place_b ON route_tasks (place_b_id)")
    
    logger.info("Migration 004: Renamed point_a_id/point_b_id to place_a_id/place_b_id (INTEGER)")


def downgrade():
    """Миграция вниз: возврат к point_a_id/point_b_id (VARCHAR)."""
    # Удаляем новые индексы
    op.execute("DROP INDEX IF EXISTS idx_route_tasks_place_a")
    op.execute("DROP INDEX IF EXISTS idx_route_tasks_place_b")
    
    # Добавляем старые колонки
    op.execute("""
        ALTER TABLE route_tasks 
        ADD COLUMN IF NOT EXISTS point_a_id VARCHAR NOT NULL DEFAULT ''
    """)
    op.execute("""
        ALTER TABLE route_tasks 
        ADD COLUMN IF NOT EXISTS point_b_id VARCHAR NOT NULL DEFAULT ''
    """)
    
    # Убираем default
    op.execute("ALTER TABLE route_tasks ALTER COLUMN point_a_id DROP DEFAULT")
    op.execute("ALTER TABLE route_tasks ALTER COLUMN point_b_id DROP DEFAULT")
    
    # Удаляем новые колонки
    op.execute("ALTER TABLE route_tasks DROP COLUMN IF EXISTS place_a_id")
    op.execute("ALTER TABLE route_tasks DROP COLUMN IF EXISTS place_b_id")
    
    # Создаем старые индексы
    op.execute("CREATE INDEX IF NOT EXISTS idx_route_tasks_point_a ON route_tasks (point_a_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_route_tasks_point_b ON route_tasks (point_b_id)")
    
    logger.info("Migration 004 downgrade: Restored point_a_id/point_b_id (VARCHAR)")
