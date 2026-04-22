"""raname tag_id

Revision ID: 019
Revises: 018
Create Date: 2026-02-11 14:03:55.060484

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Переименование tag_id -> tag_name (без потери данных)
    op.drop_index('ix_tags_tag_id', table_name='tags')
    op.alter_column(
        'tags',
        'tag_id',
        new_column_name='tag_name',
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )
    op.create_index(op.f('ix_tags_tag_name'), 'tags', ['tag_name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_tags_tag_name'), table_name='tags')
    op.alter_column(
        'tags',
        'tag_name',
        new_column_name='tag_id',
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )
    op.create_index('ix_tags_tag_id', 'tags', ['tag_id'], unique=True)