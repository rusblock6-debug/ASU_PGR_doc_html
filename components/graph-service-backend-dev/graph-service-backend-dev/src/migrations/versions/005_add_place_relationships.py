"""Add level_id to places table

Revision ID: 005
Revises: 004
Create Date: 2025-11-11 12:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('places', sa.Column('level_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_places_level_id', 'places', 'levels', ['level_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_places_level_id', 'places', type_='foreignkey')
    op.drop_column('places', 'level_id')

