"""Add work system status

Revision ID: 013
Revises: 012
Create Date: 2026-02-05

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Добавить системный статус "Работа" (work).
    Этот статус используется для обобщенных интервалов смен,
    где более 60% записей имеют cycle_id.
    """
    
    op.execute("""
        INSERT INTO statuses (system_name, display_name, color, analytic_category, organization_category_id, system_status, created_at, updated_at)
        VALUES ('work', 'Работа', '#4CAF50', 'productive', NULL, true, NOW(), NOW())
        ON CONFLICT (system_name) DO NOTHING
    """)


def downgrade() -> None:
    """
    Удалить системный статус "Работа" (work).
    """
    op.execute("DELETE FROM statuses WHERE system_name = 'work'")
