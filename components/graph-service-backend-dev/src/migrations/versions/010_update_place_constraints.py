"""
Relax place location, enforce name uniqueness and start dates

Revision ID: 010
Revises: 009
Create Date: 2025-02-XX XX:XX:XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow NULL locations on the base table.
    op.alter_column(
        'places',
        'location',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )

    # Ensure place names stay unique.
    op.create_unique_constraint('uq_places_name', 'places', ['name'])


def downgrade() -> None:
    op.drop_constraint('uq_places_name', 'places', type_='unique')
    op.alter_column(
        'places',
        'location',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
    )

