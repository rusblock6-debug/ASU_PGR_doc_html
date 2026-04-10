"""Remove shift_tasks and route_tasks tables

Revision ID: 012
Revises: 011
Create Date: 2026-01-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove shift_tasks and route_tasks tables."""
    # Удаляем таблицу route_tasks (сначала, так как есть FK на shift_tasks)
    op.drop_table('route_tasks')
    
    # Удаляем таблицу shift_tasks
    op.drop_table('shift_tasks')


def downgrade() -> None:
    """Downgrade is not supported for this migration."""
    # Восстановление таблиц не реализовано, так как данные были перенесены в trip-service
    pass


