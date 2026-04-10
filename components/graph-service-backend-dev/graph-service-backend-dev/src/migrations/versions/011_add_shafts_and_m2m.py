"""Add shafts table and M2M relation with horizons

Revision ID: 011
Revises: 010
Create Date: 2025-12-03 12:00:00

Добавляет:
- Таблицу shafts (шахты)
- Ассоциативную таблицу shaft_horizons для связи многие-ко-многим
"""
from alembic import op
import sqlalchemy as sa
from loguru import logger
from sqlalchemy import func

# revision identifiers
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # 1. Создаем таблицу shafts (если не существует)
    if 'shafts' not in tables:
        op.create_table('shafts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index(op.f('ix_shafts_id'), 'shafts', ['id'], unique=False)
        logger.info("Created table 'shafts'")
    else:
        logger.warning("Table 'shafts' already exists - skipping")
    
    # 2. Создаем ассоциативную таблицу shaft_horizons (если не существует)
    if 'shaft_horizons' not in tables:
        op.create_table('shaft_horizons',
            sa.Column('shaft_id', sa.Integer(), nullable=False),
            sa.Column('horizon_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['shaft_id'], ['shafts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['horizon_id'], ['horizons.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('shaft_id', 'horizon_id')
        )
        op.create_index('ix_shaft_horizons_shaft_id', 'shaft_horizons', ['shaft_id'], unique=False)
        op.create_index('ix_shaft_horizons_horizon_id', 'shaft_horizons', ['horizon_id'], unique=False)
        logger.info("Created table 'shaft_horizons'")
    else:
        logger.warning("Table 'shaft_horizons' already exists - skipping")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # 1. Удаляем ассоциативную таблицу shaft_horizons
    if 'shaft_horizons' in tables:
        op.drop_index('ix_shaft_horizons_horizon_id', table_name='shaft_horizons')
        op.drop_index('ix_shaft_horizons_shaft_id', table_name='shaft_horizons')
        op.drop_table('shaft_horizons')
        logger.info("Dropped table 'shaft_horizons'")
    
    # 2. Удаляем таблицу shafts
    if 'shafts' in tables:
        op.drop_index(op.f('ix_shafts_id'), table_name='shafts')
        op.drop_table('shafts')
        logger.info("Dropped table 'shafts'")


