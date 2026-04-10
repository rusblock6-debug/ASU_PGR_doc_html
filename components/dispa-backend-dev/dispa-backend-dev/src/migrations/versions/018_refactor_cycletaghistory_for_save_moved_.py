"""Refactor CycleTagHistory for save moved vechicle history

Revision ID: 018
Revises: 017
Create Date: 2026-02-11 11:43:59.257797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '018'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tag_event_enum = postgresql.ENUM('entry', 'exit', name='vechicletageventenum', create_type=False)


def upgrade() -> None:
    tag_event_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('cycle_tag_history', sa.Column('place_name', sa.String(), server_default='', nullable=False))
    op.add_column('cycle_tag_history', sa.Column('place_type', sa.String(), server_default='', nullable=False))
    op.add_column('cycle_tag_history', sa.Column('tag_id', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('cycle_tag_history', sa.Column('tag_name', sa.String(), server_default='', nullable=False))
    op.add_column('cycle_tag_history', sa.Column('tag_event', tag_event_enum, server_default='entry', nullable=False))
    op.execute("UPDATE cycle_tag_history SET place_id = 0 WHERE place_id IS NULL")
    op.alter_column('cycle_tag_history', 'place_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_index('ix_cycle_tag_history_point_id', table_name='cycle_tag_history')
    op.create_index(op.f('ix_cycle_tag_history_tag_id'), 'cycle_tag_history', ['tag_id'], unique=False)
    op.drop_column('cycle_tag_history', 'extra_data')
    op.drop_column('cycle_tag_history', 'point_id')


def downgrade() -> None:
    op.add_column('cycle_tag_history', sa.Column('point_id', sa.VARCHAR(length=255), server_default='', nullable=False))
    op.add_column('cycle_tag_history', sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_cycle_tag_history_tag_id'), table_name='cycle_tag_history')
    op.create_index('ix_cycle_tag_history_point_id', 'cycle_tag_history', ['point_id'], unique=False)
    op.alter_column('cycle_tag_history', 'place_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_column('cycle_tag_history', 'tag_event')
    op.drop_column('cycle_tag_history', 'tag_name')
    op.drop_column('cycle_tag_history', 'tag_id')
    op.drop_column('cycle_tag_history', 'place_type')
    op.drop_column('cycle_tag_history', 'place_name')
    tag_event_enum.drop(op.get_bind(), checkfirst=True)

