"""Rename levels to horizons

Revision ID: 006
Revises: 005
Create Date: 2025-11-19 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from loguru import logger

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Проверяем существование таблицы levels
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'levels' not in tables:
        logger.warning("Table 'levels' does not exist - skipping migration")
        return
    
    # Переименовываем таблицу levels в horizons
    op.rename_table('levels', 'horizons')
    
    # Переименовываем индексы через drop + create (Alembic не имеет операции rename для индексов)
    horizons_indexes = inspector.get_indexes('horizons')
    for idx in horizons_indexes:
        if idx['name'] == 'ix_levels_id':
            op.drop_index('ix_levels_id', table_name='horizons')
            op.create_index('ix_horizons_id', 'horizons', ['id'], unique=False)
        elif idx['name'] == 'ix_levels_name':
            op.drop_index('ix_levels_name', table_name='horizons')
            op.create_index('ix_horizons_name', 'horizons', ['name'], unique=False)
    
    # Переименовываем колонки через Alembic операции
    graph_nodes_columns = [col['name'] for col in inspector.get_columns('graph_nodes')]
    graph_edges_columns = [col['name'] for col in inspector.get_columns('graph_edges')]
    tags_columns = [col['name'] for col in inspector.get_columns('tags')]
    
    if 'level_id' in graph_nodes_columns:
        op.alter_column('graph_nodes', 'level_id', new_column_name='horizon_id')
    if 'level_id' in graph_edges_columns:
        op.alter_column('graph_edges', 'level_id', new_column_name='horizon_id')
    if 'level_id' in tags_columns:
        op.alter_column('tags', 'level_id', new_column_name='horizon_id')
    
    # Переименовываем индексы для foreign keys через drop + create
    graph_nodes_indexes = inspector.get_indexes('graph_nodes')
    graph_edges_indexes = inspector.get_indexes('graph_edges')
    tags_indexes = inspector.get_indexes('tags')
    
    for idx in graph_nodes_indexes:
        if idx['name'] == 'ix_graph_nodes_level_id':
            op.drop_index('ix_graph_nodes_level_id', table_name='graph_nodes')
            op.create_index('ix_graph_nodes_horizon_id', 'graph_nodes', ['horizon_id'], unique=False)
    
    for idx in graph_edges_indexes:
        if idx['name'] == 'ix_graph_edges_level_id':
            op.drop_index('ix_graph_edges_level_id', table_name='graph_edges')
            op.create_index('ix_graph_edges_horizon_id', 'graph_edges', ['horizon_id'], unique=False)
    
    for idx in tags_indexes:
        if idx['name'] == 'ix_tags_level_id':
            op.drop_index('ix_tags_level_id', table_name='tags')
            op.create_index('ix_tags_horizon_id', 'tags', ['horizon_id'], unique=False)
    
    # Исправляем places: level_id -> horizon_id (если places существует)
    if 'places' in tables:
        places_columns = [col['name'] for col in inspector.get_columns('places')]
        if 'level_id' in places_columns:
            # Удаляем старый foreign key перед переименованием
            try:
                op.drop_constraint('fk_places_level_id', 'places', type_='foreignkey')
            except Exception:
                pass
            op.alter_column('places', 'level_id', new_column_name='horizon_id')
            # Создаем новый foreign key
            op.create_foreign_key('fk_places_horizon_id', 'places', 'horizons', ['horizon_id'], ['id'], ondelete='SET NULL')


def downgrade():
    # Откатываем изменения в обратном порядке
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Исправляем places: horizon_id -> level_id
    places_columns = [col['name'] for col in inspector.get_columns('places')]
    if 'horizon_id' in places_columns:
        try:
            op.drop_constraint('fk_places_horizon_id', 'places', type_='foreignkey')
        except Exception:
            pass
        op.alter_column('places', 'horizon_id', new_column_name='level_id')
        op.create_foreign_key('fk_places_level_id', 'places', 'levels', ['level_id'], ['id'], ondelete='SET NULL')
    
    # Переименовываем индексы для foreign keys через drop + create
    tags_indexes = inspector.get_indexes('tags')
    graph_edges_indexes = inspector.get_indexes('graph_edges')
    graph_nodes_indexes = inspector.get_indexes('graph_nodes')
    
    for idx in tags_indexes:
        if idx['name'] == 'ix_tags_horizon_id':
            op.drop_index('ix_tags_horizon_id', table_name='tags')
            op.create_index('ix_tags_level_id', 'tags', ['level_id'], unique=False)
    
    for idx in graph_edges_indexes:
        if idx['name'] == 'ix_graph_edges_horizon_id':
            op.drop_index('ix_graph_edges_horizon_id', table_name='graph_edges')
            op.create_index('ix_graph_edges_level_id', 'graph_edges', ['level_id'], unique=False)
    
    for idx in graph_nodes_indexes:
        if idx['name'] == 'ix_graph_nodes_horizon_id':
            op.drop_index('ix_graph_nodes_horizon_id', table_name='graph_nodes')
            op.create_index('ix_graph_nodes_level_id', 'graph_nodes', ['level_id'], unique=False)
    
    # Переименовываем колонки через Alembic операции
    graph_nodes_columns = [col['name'] for col in inspector.get_columns('graph_nodes')]
    graph_edges_columns = [col['name'] for col in inspector.get_columns('graph_edges')]
    tags_columns = [col['name'] for col in inspector.get_columns('tags')]
    
    if 'horizon_id' in graph_nodes_columns:
        op.alter_column('graph_nodes', 'horizon_id', new_column_name='level_id')
    if 'horizon_id' in graph_edges_columns:
        op.alter_column('graph_edges', 'horizon_id', new_column_name='level_id')
    if 'horizon_id' in tags_columns:
        op.alter_column('tags', 'horizon_id', new_column_name='level_id')
    
    # Переименовываем индексы таблицы horizons через drop + create
    horizons_indexes = inspector.get_indexes('horizons')
    for idx in horizons_indexes:
        if idx['name'] == 'ix_horizons_name':
            op.drop_index('ix_horizons_name', table_name='horizons')
            op.create_index('ix_levels_name', 'horizons', ['name'], unique=False)
        elif idx['name'] == 'ix_horizons_id':
            op.drop_index('ix_horizons_id', table_name='horizons')
            op.create_index('ix_levels_id', 'horizons', ['id'], unique=False)
    
    op.rename_table('horizons', 'levels')

