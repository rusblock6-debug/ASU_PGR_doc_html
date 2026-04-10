"""
Удаление поля tag из cycle_tag_history.

Revision ID: 002_remove_tag
Revises: 001_migrate_point_to_place
Create Date: 2025-11-26

Изменения:
1. cycle_tag_history: удалить поле tag (оно дублирует point_id)
"""

from alembic import op
import sqlalchemy as sa
from loguru import logger


revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Удаление поля tag из cycle_tag_history."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем, существует ли колонка tag
    cth_columns = {col['name']: col for col in inspector.get_columns('cycle_tag_history')}
    
    if 'tag' in cth_columns:
        op.drop_column('cycle_tag_history', 'tag')
        logger.info("Migration 002: Removed tag column from cycle_tag_history")
    else:
        logger.info("Migration 002: tag column already removed from cycle_tag_history")


def downgrade():
    """Восстановление поля tag в cycle_tag_history."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    cth_columns = {col['name']: col for col in inspector.get_columns('cycle_tag_history')}
    
    if 'tag' not in cth_columns:
        # Восстанавливаем колонку, копируя значение из point_id
        op.add_column('cycle_tag_history', sa.Column('tag', sa.String(255), nullable=True))
        
        # Копируем значения из point_id в tag
        op.execute("UPDATE cycle_tag_history SET tag = point_id WHERE tag IS NULL")
        
        # Делаем колонку NOT NULL
        op.alter_column('cycle_tag_history', 'tag', nullable=False)
        
        logger.info("Migration 002 downgrade: Restored tag column in cycle_tag_history")

