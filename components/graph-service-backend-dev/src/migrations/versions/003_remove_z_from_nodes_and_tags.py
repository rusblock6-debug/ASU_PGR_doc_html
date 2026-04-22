"""Remove z column from graph_nodes and tags - height now comes from level

Revision ID: 003
Revises: 002
Create Date: 2025-10-28 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from loguru import logger

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    """
    Удаляем колонки z из graph_nodes и tags.
    Теперь высота (z) всегда берется из level.height через relationship.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Проверяем и удаляем колонку z из graph_nodes
    nodes_columns = [col['name'] for col in inspector.get_columns('graph_nodes')]
    if 'z' in nodes_columns:
        with op.batch_alter_table('graph_nodes', schema=None) as batch_op:
            batch_op.drop_column('z')
        logger.info("Column 'z' removed from 'graph_nodes' table")
    else:
        logger.warning("Column 'z' already removed from 'graph_nodes' table - skipping")
    
    # Проверяем и удаляем колонку z из tags
    tags_columns = [col['name'] for col in inspector.get_columns('tags')]
    if 'z' in tags_columns:
        with op.batch_alter_table('tags', schema=None) as batch_op:
            batch_op.drop_column('z')
        logger.info("Column 'z' removed from 'tags' table")
    else:
        logger.warning("Column 'z' already removed from 'tags' table - skipping")

def downgrade():
    """
    Восстанавливаем колонки z, копируя значения из level.height
    """
    # Добавляем колонку z обратно в graph_nodes
    op.add_column('graph_nodes', 
        sa.Column('z', sa.Float(), nullable=True)
    )
    
    # Заполняем значениями из level.height
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE graph_nodes 
            SET z = levels.height 
            FROM levels 
            WHERE graph_nodes.level_id = levels.id
        """)
    )
    
    # Делаем колонку NOT NULL
    with op.batch_alter_table('graph_nodes', schema=None) as batch_op:
        batch_op.alter_column('z', nullable=False)
    
    # Добавляем колонку z обратно в tags
    op.add_column('tags', 
        sa.Column('z', sa.Float(), nullable=True)
    )
    
    # Заполняем значениями из level.height
    conn.execute(
        sa.text("""
            UPDATE tags 
            SET z = levels.height 
            FROM levels 
            WHERE tags.level_id = levels.id
        """)
    )
    
    # Делаем колонку NOT NULL
    with op.batch_alter_table('tags', schema=None) as batch_op:
        batch_op.alter_column('z', nullable=False)
    
    logger.info("Columns 'z' restored to 'graph_nodes' and 'tags' tables")

