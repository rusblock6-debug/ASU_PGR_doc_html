"""Add is_work_status to statuses

Revision ID: 014
Revises: 013
Create Date: 2026-02-06

Добавляет поле is_work_status в таблицу statuses.
Проставляет is_work_status=true всем системным статусам (system_status=true),
кроме idle и no_data.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Добавить колонку is_work_status
    op.add_column(
        'statuses',
        sa.Column('is_work_status', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    
    # 2. Проставить is_work_status=true для system_status=true, кроме idle и no_data
    op.execute("""
        UPDATE statuses
        SET is_work_status = true
        WHERE system_status = true
          AND (system_name IS NULL OR system_name NOT IN ('idle', 'no_data'))
    """)


def downgrade() -> None:
    op.drop_column('statuses', 'is_work_status')
