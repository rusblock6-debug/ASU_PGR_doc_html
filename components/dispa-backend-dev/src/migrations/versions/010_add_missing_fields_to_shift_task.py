"""Add shift_num and make task_name nullable in shift_tasks

Revision ID: 010
Revises: 009
Create Date: 2026-01-13
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add shift_num field and update task_name to nullable"""
    
    # 1. Добавить shift_num как nullable (временно)
    op.add_column(
        'shift_tasks',
        sa.Column('shift_num', sa.Integer(), nullable=True)
    )
    
    # 2. Заполнить shift_num для существующих записей (1 по умолчанию)
    op.execute(
        "UPDATE shift_tasks SET shift_num = 1 WHERE shift_num IS NULL"
    )
    
    # 3. Сделать shift_num NOT NULL
    op.alter_column(
        'shift_tasks',
        'shift_num',
        existing_type=sa.Integer(),
        nullable=False
    )
    
    # 4. Создать индекс на shift_num
    op.create_index(
        'ix_shift_tasks_shift_num',
        'shift_tasks',
        ['shift_num']
    )
    
    # 5. Разрешить NULL для task_name
    op.alter_column(
        'shift_tasks',
        'task_name',
        existing_type=sa.String(length=500),
        nullable=True
    )


def downgrade() -> None:
    """Rollback changes"""
    
    # Обратные операции
    op.alter_column(
        'shift_tasks',
        'task_name',
        existing_type=sa.String(length=500),
        nullable=False
    )
    
    op.drop_index('ix_shift_tasks_shift_num', table_name='shift_tasks')
    
    op.drop_column('shift_tasks', 'shift_num')



