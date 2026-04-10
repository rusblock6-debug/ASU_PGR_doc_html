"""Add color column to levels table

Revision ID: 002
Revises: 001
Create Date: 2025-10-22 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from loguru import logger

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Проверяем существование колонки перед добавлением
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем существует ли колонка 'color' в таблице 'levels'
    columns = [col['name'] for col in inspector.get_columns('levels')]
    
    if 'color' not in columns:
        # Колонки нет - добавляем
        op.add_column('levels', 
            sa.Column('color', sa.String(length=7), nullable=True, server_default='#2196F3')
        )
        logger.info("Column 'color' added to 'levels' table")
        
        # Обновляем существующие строки (если есть) - устанавливаем дефолтный цвет
        conn.execute(
            sa.text("UPDATE levels SET color = '#2196F3' WHERE color IS NULL")
        )
        logger.info("Updated existing levels with default color '#2196F3'")
    else:
        # Колонка уже существует - пропускаем добавление
        logger.warning("Column 'color' already exists in 'levels' table - skipping")
        
        # НО проверяем есть ли строки с NULL цветом и обновляем их
        # result = conn.execute(
        #     sa.text("SELECT COUNT(*) FROM levels WHERE color IS NULL")
        # )
        # null_count = result.scalar()
        #
        # if null_count > 0:
        #     conn.execute(
        #         sa.text("UPDATE levels SET color = '#2196F3' WHERE color IS NULL")
        #     )
        #     print(f"✅ Updated {null_count} existing levels with default color '#2196F3'")

def downgrade():
    # Удаляем колонку color
    with op.batch_alter_table('levels', schema=None) as batch_op:
        batch_op.drop_column('color')

