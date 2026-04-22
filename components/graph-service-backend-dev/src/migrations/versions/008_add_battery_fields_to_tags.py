"""Add battery fields to tags table

Revision ID: 008
Revises: 007
Create Date: 2025-11-19 12:00:00

Добавляет поля батареи в таблицу tags:
- battery_level: уровень заряда (0-100)
- battery_updated_at: дата изменения уровня заряда
"""
from alembic import op
import sqlalchemy as sa
from loguru import logger

# revision identifiers
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Проверяем существование таблицы tags
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'tags' not in tables:
        logger.warning("Table 'tags' does not exist - skipping migration")
        return
    
    tags_columns = [col['name'] for col in inspector.get_columns('tags')]
    
    # Добавляем новые поля, если их еще нет
    if 'battery_level' not in tags_columns:
        op.add_column('tags', sa.Column('battery_level', sa.Float(), nullable=True))
    
    if 'battery_updated_at' not in tags_columns:
        op.add_column('tags', sa.Column('battery_updated_at', sa.DateTime(), nullable=True))


def downgrade():
    # Проверяем существование таблицы tags
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'tags' not in tables:
        logger.warning("Table 'tags' does not exist - skipping downgrade")
        return
    
    tags_columns = [col['name'] for col in inspector.get_columns('tags')]
    
    # Удаляем поля
    if 'battery_updated_at' in tags_columns:
        op.drop_column('tags', 'battery_updated_at')
    if 'battery_level' in tags_columns:
        op.drop_column('tags', 'battery_level')

