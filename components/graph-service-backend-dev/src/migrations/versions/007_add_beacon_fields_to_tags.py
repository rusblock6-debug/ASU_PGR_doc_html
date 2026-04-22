"""Add beacon fields to tags table

Revision ID: 007
Revises: 006
Create Date: 2025-11-19 12:00:00

Добавляет поля beacon в таблицу tags:
- beacon_id: уникальная ID метки
- beacon_mac: MAC адрес метки
- beacon_place: место установки (из выпадающего списка)
"""
from alembic import op
import sqlalchemy as sa
from loguru import logger

# revision identifiers
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Проверяем существование таблицы tags
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'tags' not in tables:
        logger.warning("Table 'tags' does not exist - skipping migration")
        return
    
    tags_columns = [col['name'] for col in inspector.get_columns('tags')]
    
    # Добавляем новые поля, если их еще нет
    if 'beacon_id' not in tags_columns:
        op.add_column('tags', sa.Column('beacon_id', sa.String(100), nullable=True))
        op.create_index('ix_tags_beacon_id', 'tags', ['beacon_id'], unique=True)
    
    if 'beacon_mac' not in tags_columns:
        op.add_column('tags', sa.Column('beacon_mac', sa.String(17), nullable=True))
        op.create_index('ix_tags_beacon_mac', 'tags', ['beacon_mac'], unique=True)
    
    if 'beacon_place' not in tags_columns:
        op.add_column('tags', sa.Column('beacon_place', sa.String(200), nullable=True))
    
    # Копируем point_id в beacon_id для обратной совместимости через SQLAlchemy Core
    if 'beacon_id' in tags_columns:
        # Поле уже существует, просто обновляем NULL значения
        from sqlalchemy import Table, MetaData
        metadata = MetaData()
        tags_table = Table('tags', metadata, autoload_with=conn)
        stmt = tags_table.update().where(
            tags_table.c.beacon_id.is_(None)
        ).values(beacon_id=tags_table.c.point_id)
        conn.execute(stmt)
    else:
        # Поле только что добавлено, копируем все значения
        from sqlalchemy import Table, MetaData
        metadata = MetaData()
        tags_table = Table('tags', metadata, autoload_with=conn)
        stmt = tags_table.update().where(
            tags_table.c.beacon_id.is_(None)
        ).values(beacon_id=tags_table.c.point_id)
        conn.execute(stmt)


def downgrade():
    # Проверяем существование таблицы tags
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'tags' not in tables:
        logger.warning("Table 'tags' does not exist - skipping downgrade")
        return
    
    tags_columns = [col['name'] for col in inspector.get_columns('tags')]
    
    # Удаляем индексы
    if 'beacon_mac' in tags_columns:
        try:
            op.drop_index('ix_tags_beacon_mac', 'tags')
        except Exception:
            pass
    
    if 'beacon_id' in tags_columns:
        try:
            op.drop_index('ix_tags_beacon_id', 'tags')
        except Exception:
            pass
    
    # Удаляем поля
    if 'beacon_place' in tags_columns:
        op.drop_column('tags', 'beacon_place')
    if 'beacon_mac' in tags_columns:
        op.drop_column('tags', 'beacon_mac')
    if 'beacon_id' in tags_columns:
        op.drop_column('tags', 'beacon_id')

