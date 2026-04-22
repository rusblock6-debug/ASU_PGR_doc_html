"""Add type_task to route_tasks

Revision ID: 012
Revises: 011
Create Date: 2026-01-19

Добавляет:
1. type_task (VARCHAR) в route_tasks
"""
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Миграция вверх:
    1. Добавить type_task в route_tasks (VARCHAR)
    """
    
    # ============================================
    # 1. Добавить type_task в route_tasks
    # ============================================
    
    # 1.1. Добавить колонку type_task (nullable временно для существующих записей)
    op.add_column(
        'route_tasks',
        sa.Column('type_task', sa.String(50), nullable=True)
    )
    
    # 1.2. Заполнить дефолтным значением для существующих записей
    op.execute("""
        UPDATE route_tasks 
        SET type_task = 'loading_shas' 
        WHERE type_task IS NULL
    """)
    
    # 1.3. Сделать колонку NOT NULL
    op.alter_column(
        'route_tasks',
        'type_task',
        nullable=False
    )
    
    # 1.4. Создать индекс на type_task
    op.create_index(
        'ix_route_tasks_type_task',
        'route_tasks',
        ['type_task']
    )


def downgrade() -> None:
    """
    Откат миграции:
    1. Удалить type_task из route_tasks
    """
    
    # ============================================
    # 1. Удалить type_task из route_tasks
    # ============================================
    
    # 1.1. Удалить индекс
    op.drop_index('ix_route_tasks_type_task', table_name='route_tasks')
    
    # 1.2. Удалить колонку
    op.drop_column('route_tasks', 'type_task')

