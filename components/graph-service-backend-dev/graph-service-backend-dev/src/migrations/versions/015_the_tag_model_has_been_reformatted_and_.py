"""The Tag model has been reformatted, and the direction of communication with the Places model has been changed

Revision ID: 015 
Revises: 014
Create Date: 2025-12-18 08:20:17.550363

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # создаем связь с таблице place, для того чтобы из нее тянуть все данные в таблицу tag
    op.add_column('tags', sa.Column('place_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_tags_place_id'), 'tags', ['place_id'], unique=False)
    op.create_foreign_key(None, 'tags', 'places', ['place_id'], ['id'], ondelete='SET NULL')

    # в таблице places удалаяем поле ix_places_tag_point_id так как связь развернули и полу больше не нужно
    op.drop_index('ix_places_tag_point_id', table_name='places')
    op.drop_constraint('places_tag_point_id_fkey', 'places', type_='foreignkey')
    op.drop_column('places', 'tag_point_id')

    # данные полу убираются так как эта информация будет браться из связанной таблицы places
    op.drop_column('tags', 'beacon_place')
    op.drop_index('idx_tags_geometry', table_name='tags', postgresql_using='gist')
    op.drop_index('idx_tags_zone_geometry', table_name='tags', postgresql_using='gist')
    op.drop_column('tags', 'geometry')
    op.drop_column('tags', 'zone_geometry')

    # Удаление ненужных полей
    # X, Y удаляем 100%
    op.drop_column('tags', 'x')
    op.drop_column('tags', 'y')
    
    # mac_address = bacon_mac дублирование !?
    op.drop_column('tags', 'mac_address')

    # Пока убираем поле beacon_id, т.к. оно не используется и дублирует point_id и id
    op.drop_column('tags', 'beacon_id')
    op.drop_column('tags', 'point_type')
    
    # Убираем связь таблицы Tag с таблицей Horizon
    op.drop_index('ix_tags_horizon_id', table_name='tags')
    op.drop_constraint('tags_level_id_fkey', 'tags', type_='foreignkey')
    op.drop_column('tags', 'horizon_id')

    # Переименовываем поля place_id и bacon_id
    op.alter_column(
        'tags', 
        'point_id', 
        new_column_name='tag_id',
        existing_type=sa.String(length=100),
        existing_nullable=False
        )
    op.alter_column(
        'tags', 
        'beacon_mac', 
        new_column_name='tag_mac',
        existing_type=sa.String(length=17),
        existing_nullable=True
        )
    op.drop_index('ix_tags_beacon_mac', table_name='tags')
    op.drop_index('ix_tags_point_id', table_name='tags')
    op.create_index(op.f('ix_tags_tag_id'), 'tags', ['tag_id'], unique=True)
    op.create_index(op.f('ix_tags_tag_mac'), 'tags', ['tag_mac'], unique=True)

def downgrade() -> None:
    op.alter_column(
        'tags', 
        'tag_id',
        new_column_name='point_id',
        existing_type=sa.String(length=100),
        existing_nullable=False
        )
    op.alter_column(
        'tags', 
        'tag_mac', 
        new_column_name='beacon_mac',
        existing_type=sa.String(length=17),
        existing_nullable=True
        )
    op.drop_index(op.f('ix_tags_tag_mac'), table_name='tags')
    op.drop_index(op.f('ix_tags_tag_id'), table_name='tags')
    op.create_index('ix_tags_point_id', 'tags', ['point_id'], unique=True)
    op.create_index('ix_tags_beacon_mac', 'tags', ['beacon_mac'], unique=True)
    op.add_column('tags', sa.Column('point_type', sa.VARCHAR(length=50), autoincrement=False, nullable=False))
    op.add_column('places', sa.Column('tag_point_id', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.create_foreign_key('places_tag_point_id_fkey', 'places', 'tags', ['tag_point_id'], ['point_id'])
    op.create_index('ix_places_tag_point_id', 'places', ['tag_point_id'], unique=False)
    op.add_column('tags', sa.Column('beacon_id', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.add_column('tags', sa.Column('mac_address', sa.VARCHAR(length=17), autoincrement=False, nullable=True))
    op.add_column('tags', sa.Column('y', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    op.add_column('tags', sa.Column('x', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    op.drop_index(op.f('ix_tags_place_id'), table_name='tags')
    op.drop_column('tags', 'place_id')
    op.add_column('tags', sa.Column('zone_geometry', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', nullable=False, _spatial_index_reflected=True), autoincrement=False, nullable=False))
    op.add_column('tags', sa.Column('beacon_place', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    op.add_column('tags', sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', nullable=False, _spatial_index_reflected=True), autoincrement=False, nullable=False))
    op.create_index('idx_tags_zone_geometry', 'tags', ['zone_geometry'], unique=False, postgresql_using='gist')
    op.create_index('idx_tags_geometry', 'tags', ['geometry'], unique=False, postgresql_using='gist')
    op.add_column('tags', sa.Column('horizon_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('tags_level_id_fkey', 'tags', 'horizons', ['horizon_id'], ['id'])
    op.create_index('ix_tags_horizon_id', 'tags', ['horizon_id'], unique=False)
