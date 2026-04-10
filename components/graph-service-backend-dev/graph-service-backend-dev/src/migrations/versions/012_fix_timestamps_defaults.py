"""Fix timestamps server defaults for all tables

Revision ID: 012
Revises: 011
Create Date: 2025-12-03 14:00:00

Добавляет server_default для колонок created_at и updated_at во всех таблицах
"""
from alembic import op
import sqlalchemy as sa
from loguru import logger

# revision identifiers
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


# Таблицы которые нужно исправить
TABLES_TO_FIX = ['horizons', 'graph_nodes', 'graph_edges', 'tags', 'shafts']


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    for table_name in TABLES_TO_FIX:
        if table_name not in tables:
            logger.warning(f"Table '{table_name}' does not exist - skipping")
            continue
        
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        if 'created_at' in columns:
            try:
                op.alter_column(
                    table_name,
                    'created_at',
                    server_default=sa.text('NOW()'),
                    existing_type=sa.DateTime(),
                    existing_nullable=False
                )
            except Exception as e:
                logger.warning(f"Could not alter created_at in '{table_name}': {e}")
        
        if 'updated_at' in columns:
            try:
                op.alter_column(
                    table_name,
                    'updated_at',
                    server_default=sa.text('NOW()'),
                    existing_type=sa.DateTime(),
                    existing_nullable=False
                )
            except Exception as e:
                logger.warning(f"Could not alter updated_at in '{table_name}': {e}")
        
        logger.info(f"Fixed timestamps defaults for '{table_name}'")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    for table_name in TABLES_TO_FIX:
        if table_name not in tables:
            continue
        
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        if 'created_at' in columns:
            try:
                op.alter_column(
                    table_name,
                    'created_at',
                    server_default=None,
                    existing_type=sa.DateTime(),
                    existing_nullable=False
                )
            except Exception:
                pass
        
        if 'updated_at' in columns:
            try:
                op.alter_column(
                    table_name,
                    'updated_at',
                    server_default=None,
                    existing_type=sa.DateTime(),
                    existing_nullable=False
                )
            except Exception:
                pass
        
        logger.info(f"Removed timestamps defaults from '{table_name}'")
