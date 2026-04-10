"""drop field name from Tag table

Revision ID: 017
Revises: 016
Create Date: 2025-12-25 17:27:56.406417

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('tags', 'tag_mac',
               existing_type=sa.VARCHAR(length=17),
               nullable=False)
    op.drop_column('tags', 'name')


def downgrade() -> None:
    op.add_column('tags', sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.alter_column('tags', 'tag_mac',
               existing_type=sa.VARCHAR(length=17),
               nullable=True)