"""Add no_data system status

Revision ID: 010
Revises: 009
Create Date: 2026-01-26

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Добавить системный статус "Нет данных" (no_data).
    Этот статус используется для заполнения пустоты после удаления рейса.
    """
    
    op.execute("""
        INSERT INTO statuses (system_name, display_name, color, analytic_category, organization_category_id, system_status, created_at, updated_at)
        VALUES ('no_data', 'Нет данных', '#808080', 'unscheduled_time', NULL, true, NOW(), NOW())
        ON CONFLICT (system_name) DO NOTHING
    """)


def downgrade() -> None:
    """
    Удалить системный статус "Нет данных" (no_data).
    """
    op.execute("DELETE FROM statuses WHERE system_name = 'no_data'")
