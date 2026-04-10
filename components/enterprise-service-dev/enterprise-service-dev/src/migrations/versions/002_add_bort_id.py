"""add_bort_id_to_vehicles

Revision ID: 002
Revises: 001
Create Date: 2025-11-12 17:26:00.000000

"""
from alembic import op
import sqlalchemy as sa
from loguru import logger


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Миграция вверх: добавление столбца bort_id (идемпотентная)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем существует ли колонка 'bort_id' в таблице 'vehicles'
    columns = [col['name'] for col in inspector.get_columns('vehicles')]
    
    if 'bort_id' not in columns:
        # Колонки нет - добавляем
        op.add_column(
            "vehicles",
            sa.Column(
                "bort_id",
                sa.String(100),
                nullable=False,
                server_default="4_truck",
            ),
        )
        # Обновляем существующие строки с NULL значениями (если есть)
        op.execute("UPDATE vehicles SET bort_id = '4_truck' WHERE bort_id IS NULL")
        logger.info("Column 'bort_id' added to 'vehicles' table")
    else:
        # Колонка уже существует - пропускаем добавление
        logger.info("Column 'bort_id' already exists in 'vehicles' table - skipping")
        
        # Но обновляем существующие строки с NULL значениями (если есть)
        op.execute("UPDATE vehicles SET bort_id = '4_truck' WHERE bort_id IS NULL")


def downgrade() -> None:
    """Миграция вниз: удаление столбца bort_id."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем существует ли колонка перед удалением
    columns = [col['name'] for col in inspector.get_columns('vehicles')]
    
    if 'bort_id' in columns:
        op.drop_column("vehicles", "bort_id")
        logger.info("Column 'bort_id' removed from 'vehicles' table")
    else:
        logger.info("Column 'bort_id' already removed from 'vehicles' table - skipping")
