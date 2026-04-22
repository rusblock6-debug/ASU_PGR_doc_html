"""Add volume, weight, message fields to route_tasks

Revision ID: 011
Revises: 010
Create Date: 2026-01-13
"""
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add volume, weight, message fields"""
    
    # 1. Добавить volume
    op.add_column(
        'route_tasks',
        sa.Column('volume', sa.Float(), nullable=True, comment='Объем груза')
    )
    
    # 2. Добавить weight
    op.add_column(
        'route_tasks',
        sa.Column('weight', sa.Float(), nullable=True, comment='Вес груза')
    )
    
    # 3. Добавить message
    op.add_column(
        'route_tasks',
        sa.Column('message', sa.String(length=500), nullable=True, comment='Сообщение/комментарий к маршруту')
    )


def downgrade() -> None:
    """Rollback changes"""
    
    op.drop_column('route_tasks', 'message')
    op.drop_column('route_tasks', 'weight')
    op.drop_column('route_tasks', 'volume')



