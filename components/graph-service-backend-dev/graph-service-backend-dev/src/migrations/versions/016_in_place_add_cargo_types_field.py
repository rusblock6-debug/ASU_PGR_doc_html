"""in place add cargo types field

Revision ID: 016
Revises: 015
Create Date: 2025-12-24 08:36:16.042763

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('places', sa.Column('cargo_type', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('places', 'cargo_type')