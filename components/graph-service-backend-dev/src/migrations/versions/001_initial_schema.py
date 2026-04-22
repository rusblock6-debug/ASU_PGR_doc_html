"""Initial schema with ladder support

Revision ID: 001
Revises: 
Create Date: 2025-10-08 15:00:00
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Создание таблицы levels
    op.create_table('levels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('height', sa.Float(), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True, server_default='#2196F3'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_levels_id'), 'levels', ['id'], unique=False)
    op.create_index(op.f('ix_levels_name'), 'levels', ['name'], unique=False)

    # Создание таблицы graph_nodes (с поддержкой ladder)
    op.create_table('graph_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level_id', sa.Integer(), nullable=False),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('z', sa.Float(), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('linked_nodes', sa.Text(), nullable=True),  # Для ladder узлов
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('geometry', Geometry(geometry_type='POINT', srid=4326), nullable=False),
        sa.ForeignKeyConstraint(['level_id'], ['levels.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_graph_nodes_id'), 'graph_nodes', ['id'], unique=False)
    op.create_index(op.f('ix_graph_nodes_level_id'), 'graph_nodes', ['level_id'], unique=False)
    # GIST индекс для geometry создается автоматически GeoAlchemy2

    # Создание таблицы tags
    op.create_table('tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level_id', sa.Integer(), nullable=False),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('z', sa.Float(), nullable=False),
        sa.Column('radius', sa.Float(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('point_type', sa.String(length=50), nullable=False),
        sa.Column('point_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('geometry', Geometry(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('zone_geometry', Geometry(geometry_type='POLYGON', srid=4326), nullable=False),
        sa.ForeignKeyConstraint(['level_id'], ['levels.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('point_id')
    )
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=False)
    op.create_index(op.f('ix_tags_level_id'), 'tags', ['level_id'], unique=False)
    op.create_index(op.f('ix_tags_point_id'), 'tags', ['point_id'], unique=False)
    # GIST индексы для geometry и zone_geometry создаются автоматически GeoAlchemy2

    # Создание таблицы vehicle_locations
    op.create_table('vehicle_locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.String(length=50), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('geometry', Geometry(geometry_type='POINT', srid=4326), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicle_locations_id'), 'vehicle_locations', ['id'], unique=False)
    op.create_index(op.f('ix_vehicle_locations_vehicle_id'), 'vehicle_locations', ['vehicle_id'], unique=False)
    op.create_index(op.f('ix_vehicle_locations_timestamp'), 'vehicle_locations', ['timestamp'], unique=False)
    # GIST индекс для geometry создается автоматически GeoAlchemy2

    # Создание таблицы graph_edges (с поддержкой vertical edges)
    op.create_table('graph_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level_id', sa.Integer(), nullable=True),  # Nullable для межуровневых ребер
        sa.Column('from_node_id', sa.Integer(), nullable=False),
        sa.Column('to_node_id', sa.Integer(), nullable=False),
        sa.Column('edge_type', sa.String(length=20), nullable=False, server_default='horizontal'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('geometry', Geometry(geometry_type='LINESTRING', srid=4326), nullable=False),
        sa.ForeignKeyConstraint(['from_node_id'], ['graph_nodes.id'], ),
        sa.ForeignKeyConstraint(['level_id'], ['levels.id'], ),
        sa.ForeignKeyConstraint(['to_node_id'], ['graph_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_graph_edges_id'), 'graph_edges', ['id'], unique=False)
    op.create_index(op.f('ix_graph_edges_level_id'), 'graph_edges', ['level_id'], unique=False)
    # GIST индекс для geometry создается автоматически GeoAlchemy2


def downgrade():
    # Удаление таблиц в обратном порядке
    # GIST индексы geometry удалятся автоматически с таблицами
    op.drop_index(op.f('ix_graph_edges_level_id'), table_name='graph_edges')
    op.drop_index(op.f('ix_graph_edges_id'), table_name='graph_edges')
    op.drop_table('graph_edges')
    
    op.drop_index(op.f('ix_vehicle_locations_timestamp'), table_name='vehicle_locations')
    op.drop_index(op.f('ix_vehicle_locations_vehicle_id'), table_name='vehicle_locations')
    op.drop_index(op.f('ix_vehicle_locations_id'), table_name='vehicle_locations')
    op.drop_table('vehicle_locations')
    
    op.drop_index(op.f('ix_tags_point_id'), table_name='tags')
    op.drop_index(op.f('ix_tags_level_id'), table_name='tags')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_table('tags')
    
    op.drop_index(op.f('ix_graph_nodes_level_id'), table_name='graph_nodes')
    op.drop_index(op.f('ix_graph_nodes_id'), table_name='graph_nodes')
    op.drop_table('graph_nodes')
    
    op.drop_index(op.f('ix_levels_name'), table_name='levels')
    op.drop_index(op.f('ix_levels_id'), table_name='levels')
    op.drop_table('levels')
