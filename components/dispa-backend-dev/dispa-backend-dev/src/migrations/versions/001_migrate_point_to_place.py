"""
Миграция с point_id на place_id во всех таблицах.

Revision ID: 001_migrate_point_to_place
Revises: 000_initial_schema
Create Date: 2025-01-01

Изменения:
1. route_tasks: point_a_id, point_b_id (String) -> place_a_id, place_b_id (Integer)
2. cycles: from_point_id, to_point_id (String) -> from_place_id, to_place_id (Integer)
3. trips: loading_point_id, unloading_point_id (String) -> loading_place_id, unloading_place_id (Integer)
4. cycle_tag_history: добавить place_id (Integer)
5. cycle_analytics: from_point_id, to_point_id (String) -> from_place_id, to_place_id (Integer)
"""

from alembic import op
import sqlalchemy as sa
from loguru import logger


revision = '001'
down_revision = '000'
branch_labels = None
depends_on = None


def upgrade():
    """Миграция вверх: переход с point_id на place_id."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # === route_tasks ===
    rt_columns = {col['name']: col for col in inspector.get_columns('route_tasks')}
    
    # Удаляем старые индексы если есть
    try:
        op.drop_index('ix_route_tasks_status_point_a', table_name='route_tasks')
    except Exception:
        pass
    
    # Удаляем старые колонки
    if 'point_a_id' in rt_columns:
        op.drop_column('route_tasks', 'point_a_id')
    if 'point_b_id' in rt_columns:
        op.drop_column('route_tasks', 'point_b_id')
    
    # Добавляем новые колонки
    rt_columns = {col['name']: col for col in inspector.get_columns('route_tasks')}
    if 'place_a_id' not in rt_columns:
        op.add_column('route_tasks', sa.Column('place_a_id', sa.Integer(), nullable=False, server_default='0'))
        op.alter_column('route_tasks', 'place_a_id', server_default=None)
    if 'place_b_id' not in rt_columns:
        op.add_column('route_tasks', sa.Column('place_b_id', sa.Integer(), nullable=False, server_default='0'))
        op.alter_column('route_tasks', 'place_b_id', server_default=None)
    
    # Создаем новые индексы
    op.create_index('ix_route_tasks_status_place_a', 'route_tasks', ['status', 'place_a_id'])
    op.create_index('ix_route_tasks_place_a_id', 'route_tasks', ['place_a_id'])
    
    # === cycles ===
    cycles_columns = {col['name']: col for col in inspector.get_columns('cycles')}
    
    if 'from_point_id' in cycles_columns:
        op.drop_column('cycles', 'from_point_id')
    if 'to_point_id' in cycles_columns:
        op.drop_column('cycles', 'to_point_id')
    
    cycles_columns = {col['name']: col for col in inspector.get_columns('cycles')}
    if 'from_place_id' not in cycles_columns:
        op.add_column('cycles', sa.Column('from_place_id', sa.Integer(), nullable=True))
    if 'to_place_id' not in cycles_columns:
        op.add_column('cycles', sa.Column('to_place_id', sa.Integer(), nullable=True))
    
    # === trips ===
    trips_columns = {col['name']: col for col in inspector.get_columns('trips')}
    
    if 'loading_point_id' in trips_columns:
        op.drop_column('trips', 'loading_point_id')
    if 'unloading_point_id' in trips_columns:
        op.drop_column('trips', 'unloading_point_id')
    
    trips_columns = {col['name']: col for col in inspector.get_columns('trips')}
    if 'loading_place_id' not in trips_columns:
        op.add_column('trips', sa.Column('loading_place_id', sa.Integer(), nullable=True))
    if 'unloading_place_id' not in trips_columns:
        op.add_column('trips', sa.Column('unloading_place_id', sa.Integer(), nullable=True))
    
    # === cycle_tag_history ===
    cth_columns = {col['name']: col for col in inspector.get_columns('cycle_tag_history')}
    
    if 'place_id' not in cth_columns:
        op.add_column('cycle_tag_history', sa.Column('place_id', sa.Integer(), nullable=True))
        op.create_index('ix_cycle_tag_history_place_id', 'cycle_tag_history', ['place_id'])
    
    # === cycle_analytics ===
    ca_columns = {col['name']: col for col in inspector.get_columns('cycle_analytics')}
    
    if 'from_point_id' in ca_columns:
        op.drop_column('cycle_analytics', 'from_point_id')
    if 'to_point_id' in ca_columns:
        op.drop_column('cycle_analytics', 'to_point_id')
    
    ca_columns = {col['name']: col for col in inspector.get_columns('cycle_analytics')}
    if 'from_place_id' not in ca_columns:
        op.add_column('cycle_analytics', sa.Column('from_place_id', sa.Integer(), nullable=True))
    if 'to_place_id' not in ca_columns:
        op.add_column('cycle_analytics', sa.Column('to_place_id', sa.Integer(), nullable=True))
    
    logger.info("Migration 001: Migrated point_id to place_id in all tables")


def downgrade():
    """Миграция вниз: возврат к point_id."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # === route_tasks ===
    try:
        op.drop_index('ix_route_tasks_status_place_a', table_name='route_tasks')
    except Exception:
        pass
    try:
        op.drop_index('ix_route_tasks_place_a_id', table_name='route_tasks')
    except Exception:
        pass
    
    rt_columns = {col['name']: col for col in inspector.get_columns('route_tasks')}
    if 'place_a_id' in rt_columns:
        op.drop_column('route_tasks', 'place_a_id')
    if 'place_b_id' in rt_columns:
        op.drop_column('route_tasks', 'place_b_id')
    
    rt_columns = {col['name']: col for col in inspector.get_columns('route_tasks')}
    if 'point_a_id' not in rt_columns:
        op.add_column('route_tasks', sa.Column('point_a_id', sa.String(255), nullable=False, server_default=''))
        op.alter_column('route_tasks', 'point_a_id', server_default=None)
    if 'point_b_id' not in rt_columns:
        op.add_column('route_tasks', sa.Column('point_b_id', sa.String(255), nullable=False, server_default=''))
        op.alter_column('route_tasks', 'point_b_id', server_default=None)
    
    op.create_index('ix_route_tasks_status_point_a', 'route_tasks', ['status', 'point_a_id'])
    
    # === cycles ===
    cycles_columns = {col['name']: col for col in inspector.get_columns('cycles')}
    if 'from_place_id' in cycles_columns:
        op.drop_column('cycles', 'from_place_id')
    if 'to_place_id' in cycles_columns:
        op.drop_column('cycles', 'to_place_id')
    
    cycles_columns = {col['name']: col for col in inspector.get_columns('cycles')}
    if 'from_point_id' not in cycles_columns:
        op.add_column('cycles', sa.Column('from_point_id', sa.String(255), nullable=True))
    if 'to_point_id' not in cycles_columns:
        op.add_column('cycles', sa.Column('to_point_id', sa.String(255), nullable=True))
    
    # === trips ===
    trips_columns = {col['name']: col for col in inspector.get_columns('trips')}
    if 'loading_place_id' in trips_columns:
        op.drop_column('trips', 'loading_place_id')
    if 'unloading_place_id' in trips_columns:
        op.drop_column('trips', 'unloading_place_id')
    
    trips_columns = {col['name']: col for col in inspector.get_columns('trips')}
    if 'loading_point_id' not in trips_columns:
        op.add_column('trips', sa.Column('loading_point_id', sa.String(255), nullable=True))
    if 'unloading_point_id' not in trips_columns:
        op.add_column('trips', sa.Column('unloading_point_id', sa.String(255), nullable=True))
    
    # === cycle_tag_history ===
    try:
        op.drop_index('ix_cycle_tag_history_place_id', table_name='cycle_tag_history')
    except Exception:
        pass
    
    cth_columns = {col['name']: col for col in inspector.get_columns('cycle_tag_history')}
    if 'place_id' in cth_columns:
        op.drop_column('cycle_tag_history', 'place_id')
    
    # === cycle_analytics ===
    ca_columns = {col['name']: col for col in inspector.get_columns('cycle_analytics')}
    if 'from_place_id' in ca_columns:
        op.drop_column('cycle_analytics', 'from_place_id')
    if 'to_place_id' in ca_columns:
        op.drop_column('cycle_analytics', 'to_place_id')
    
    ca_columns = {col['name']: col for col in inspector.get_columns('cycle_analytics')}
    if 'from_point_id' not in ca_columns:
        op.add_column('cycle_analytics', sa.Column('from_point_id', sa.String(255), nullable=True))
    if 'to_point_id' not in ca_columns:
        op.add_column('cycle_analytics', sa.Column('to_point_id', sa.String(255), nullable=True))
    
    logger.info("Migration 001 downgrade: Restored point_id in all tables")

