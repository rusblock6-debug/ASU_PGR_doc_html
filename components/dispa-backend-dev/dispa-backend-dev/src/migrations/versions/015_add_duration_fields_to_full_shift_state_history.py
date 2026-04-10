"""Add duration fields to full_shift_state_history

Revision ID: 015
Revises: 014
Create Date: 2026-02-06

Добавляет поля idle_duration и work_duration в таблицу full_shift_state_history
для хранения длительностей работы и простоя в секундах.
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Добавить поля idle_duration и work_duration.
    
    - idle_duration: длительность простоя в секундах (статусы с is_work_status=false)
    - work_duration: длительность работы в секундах (статусы с is_work_status=true)
    """
    op.add_column(
        'full_shift_state_history',
        sa.Column('idle_duration', sa.Integer(), nullable=True)
    )
    op.add_column(
        'full_shift_state_history',
        sa.Column('work_duration', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """
    Удалить поля idle_duration и work_duration.
    """
    op.drop_column('full_shift_state_history', 'work_duration')
    op.drop_column('full_shift_state_history', 'idle_duration')
