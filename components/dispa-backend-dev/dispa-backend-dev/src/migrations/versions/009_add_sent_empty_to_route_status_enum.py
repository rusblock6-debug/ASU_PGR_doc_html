"""Migration 007 - no longer needed

Revision ID: 009
Revises: 008
Create Date: 2026-01-13

Эта миграция больше не нужна - статусы хранятся как VARCHAR,
новые значения ('sent', 'empty') добавляются автоматически через SQLAlchemy.
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Миграция больше не нужна - статусы хранятся как VARCHAR.
    Новые значения ('sent', 'empty') добавляются автоматически через SQLAlchemy.
    """
    pass


def downgrade() -> None:
    """
    Откат: миграция пустая, откат не требуется.
    """
    pass



