"""Add vehicle model relationship

Revision ID: 005
Revises: 004
Create Date: 2025-12-01 10:58:13.958828

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаём таблицу vehicle_models
    op.create_table('vehicle_models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('max_speed', sa.Integer(), nullable=True),
        sa.Column('tank_volume', sa.Float(), nullable=True),
        sa.Column('load_capacity_tons', sa.Float(), nullable=True),
        sa.Column('volume_m3', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Добавляем колонку model_id в vehicles
    op.add_column('vehicles', sa.Column('model_id', sa.Integer(), nullable=True))
    
    # Создаём foreign key
    op.create_foreign_key('fk_vehicles_model_id', 'vehicles', 'vehicle_models', ['model_id'], ['id'])


def downgrade() -> None:
    # Удаляем foreign key
    op.drop_constraint('fk_vehicles_model_id', 'vehicles', type_='foreignkey')
    
    # Удаляем колонку model_id
    op.drop_column('vehicles', 'model_id')
    
    # Удаляем таблицу vehicle_models
    op.drop_table('vehicle_models')

