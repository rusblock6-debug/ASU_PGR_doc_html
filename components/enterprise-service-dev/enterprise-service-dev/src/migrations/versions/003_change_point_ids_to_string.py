"""change_point_ids_to_string

Revision ID: 003
Revises: 002
Create Date: 2025-11-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from loguru import logger


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Миграция вверх: изменение типа point_a_id и point_b_id с INTEGER на VARCHAR."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем существует ли таблица 'route_tasks'
    tables = inspector.get_table_names()
    
    if 'route_tasks' not in tables:
        logger.info("Table 'route_tasks' doesn't exist - skipping")
        return
    
    # Получаем информацию о колонках
    columns = {col['name']: col for col in inspector.get_columns('route_tasks')}
    
    # Проверяем тип колонки point_a_id
    if 'point_a_id' in columns:
        col_type = str(columns['point_a_id']['type'])
        if 'INTEGER' in col_type.upper():
            # Изменяем тип с INTEGER на VARCHAR
            # Используем USING для конвертации значений
            op.execute("""
                ALTER TABLE route_tasks 
                ALTER COLUMN point_a_id TYPE VARCHAR 
                USING point_a_id::VARCHAR
            """)
            logger.info("Column 'point_a_id' type changed from INTEGER to VARCHAR")
        else:
            logger.info(f"Column 'point_a_id' already has type {col_type} - skipping")
    
    # Проверяем тип колонки point_b_id
    if 'point_b_id' in columns:
        col_type = str(columns['point_b_id']['type'])
        if 'INTEGER' in col_type.upper():
            # Изменяем тип с INTEGER на VARCHAR
            op.execute("""
                ALTER TABLE route_tasks 
                ALTER COLUMN point_b_id TYPE VARCHAR 
                USING point_b_id::VARCHAR
            """)
            logger.info("Column 'point_b_id' type changed from INTEGER to VARCHAR")
        else:
            logger.info(f"Column 'point_b_id' already has type {col_type} - skipping")


def downgrade() -> None:
    """Миграция вниз: изменение типа point_a_id и point_b_id с VARCHAR обратно на INTEGER."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем существует ли таблица 'route_tasks'
    tables = inspector.get_table_names()
    
    if 'route_tasks' not in tables:
        logger.info("Table 'route_tasks' doesn't exist - skipping")
        return
    
    # Получаем информацию о колонках
    columns = {col['name']: col for col in inspector.get_columns('route_tasks')}
    
    # Проверяем тип колонки point_a_id
    if 'point_a_id' in columns:
        col_type = str(columns['point_a_id']['type'])
        if 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
            # Изменяем тип с VARCHAR обратно на INTEGER
            op.execute("""
                ALTER TABLE route_tasks 
                ALTER COLUMN point_a_id TYPE INTEGER 
                USING point_a_id::INTEGER
            """)
            logger.info("Column 'point_a_id' type changed from VARCHAR to INTEGER")
        else:
            logger.info(f"Column 'point_a_id' already has type {col_type} - skipping")
    
    # Проверяем тип колонки point_b_id
    if 'point_b_id' in columns:
        col_type = str(columns['point_b_id']['type'])
        if 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
            # Изменяем тип с VARCHAR обратно на INTEGER
            op.execute("""
                ALTER TABLE route_tasks 
                ALTER COLUMN point_b_id TYPE INTEGER 
                USING point_b_id::INTEGER
            """)
            logger.info("Column 'point_b_id' type changed from VARCHAR to INTEGER")
        else:
            logger.info(f"Column 'point_b_id' already has type {col_type} - skipping")

