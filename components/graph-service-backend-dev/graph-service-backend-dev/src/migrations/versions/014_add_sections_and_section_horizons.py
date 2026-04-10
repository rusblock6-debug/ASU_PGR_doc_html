"""Add sections table and M2M relation with horizons

Revision ID: 014
Revises: 013
Create Date: 2025-12-12

Добавляет:
- Таблицу sections (участки)
- Ассоциативную таблицу section_horizons для связи многие-ко-многим
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func
from loguru import logger

# revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # 1. Создаем таблицу sections (если не существует)
    if 'sections' not in tables:
        op.create_table('sections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('is_contractor_organization', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index(op.f('ix_sections_id'), 'sections', ['id'], unique=False)
        op.create_index(op.f('ix_sections_name'), 'sections', ['name'], unique=False)
        logger.info("[OK] Created table 'sections'")
    else:
        logger.info("[SKIP] Table 'sections' already exists - skipping")
    
    # 2. Создаем ассоциативную таблицу section_horizons (если не существует)
    if 'section_horizons' not in tables:
        op.create_table('section_horizons',
            sa.Column('section_id', sa.Integer(), nullable=False),
            sa.Column('horizon_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['horizon_id'], ['horizons.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('section_id', 'horizon_id')
        )
        op.create_index('ix_section_horizons_section_id', 'section_horizons', ['section_id'], unique=False)
        op.create_index('ix_section_horizons_horizon_id', 'section_horizons', ['horizon_id'], unique=False)
        logger.info("[OK] Created table 'section_horizons'")
    else:
        logger.info("[SKIP] Table 'section_horizons' already exists - skipping")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # 1. Удаляем ассоциативную таблицу section_horizons
    if 'section_horizons' in tables:
        op.drop_index('ix_section_horizons_horizon_id', table_name='section_horizons')
        op.drop_index('ix_section_horizons_section_id', table_name='section_horizons')
        op.drop_table('section_horizons')
        logger.info("[OK] Dropped table 'section_horizons'")
    
    # 2. Удаляем таблицу sections
    if 'sections' in tables:
        op.drop_index(op.f('ix_sections_name'), table_name='sections')
        op.drop_index(op.f('ix_sections_id'), table_name='sections')
        op.drop_table('sections')
        logger.info("[OK] Dropped table 'sections'")

