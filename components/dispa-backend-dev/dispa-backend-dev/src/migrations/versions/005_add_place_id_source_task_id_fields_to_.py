"""Add place_id, source, task_id fields to cycle_state_history

Revision ID: 005
Revises: 004
Create Date: 2025-12-29 20:07:25.941115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema"""
    # Add new columns to cycle_state_history table
    op.add_column('cycle_state_history', sa.Column('place_id', sa.Integer(), nullable=True, comment='ID места/точки'))
    op.add_column('cycle_state_history', sa.Column('source', sa.String(20), nullable=False, server_default='system', comment='Источник изменения: dispatcher или system'))
    op.add_column('cycle_state_history', sa.Column('task_id', sa.String(50), nullable=True, comment='ID задачи (UUID4)'))


def downgrade() -> None:
    """Downgrade schema"""
    # Remove added columns
    op.drop_column('cycle_state_history', 'task_id')
    op.drop_column('cycle_state_history', 'source')
    op.drop_column('cycle_state_history', 'place_id')

