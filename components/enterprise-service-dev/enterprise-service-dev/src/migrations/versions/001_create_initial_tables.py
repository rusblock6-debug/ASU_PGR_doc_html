"""
Create initial tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enterprise_settings table
    op.create_table(
        'enterprise_settings',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('enterprise_name', sa.String(length=200), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Europe/Moscow'),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('coordinates', postgresql.JSONB(), nullable=True),
        sa.Column('settings_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create work_regimes table
    op.create_table(
        'work_regimes',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('enterprise_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('shifts_definition', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprise_settings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_work_regimes_enterprise', 'work_regimes', ['enterprise_id'])
    op.create_index('idx_work_regimes_active', 'work_regimes', ['is_active'])

    # Create vehicles table
    op.create_table(
        'vehicles',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('enterprise_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('registration_number', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('engine_power_hp', sa.Integer(), nullable=True),
        sa.Column('tank_volume', sa.Float(), nullable=True),
        sa.Column('active_from', sa.Date(), nullable=True),
        sa.Column('active_to', sa.Date(), nullable=True),
        sa.Column('capacity_tons', sa.Float(), nullable=True),
        sa.Column('bucket_volume_m3', sa.Float(), nullable=True),
        sa.Column('payload_tons', sa.Float(), nullable=True),
        sa.Column('dump_body_volume_m3', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprise_settings.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serial_number', name='uq_vehicles_serial_number')
    )
    op.create_index('idx_vehicles_enterprise', 'vehicles', ['enterprise_id'])
    op.create_index('idx_vehicles_type', 'vehicles', ['vehicle_type'])
    op.create_index('idx_vehicles_status', 'vehicles', ['status'])
    op.create_index('idx_vehicles_active', 'vehicles', ['is_active'])


    # Create statuses table
    op.create_table(
        'statuses',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('enterprise_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=False),
        sa.Column('export_code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status_category', sa.String(length=50), nullable=True),
        sa.Column('analytic_category', sa.String(length=50), nullable=True),
        sa.Column('organization_category', sa.String(length=50), nullable=True),
        sa.Column('available_vehicle_types', sa.String(length=50), nullable=True),
        sa.Column('is_plan', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('standard_duration', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['enterprise_id'], ['enterprise_settings.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('export_code', name='uq_statuses_export_code')
    )
    op.create_index('idx_statuses_enterprise', 'statuses', ['enterprise_id'])
    op.create_index('idx_statuses_category', 'statuses', ['status_category'])
    op.create_index('idx_statuses_active', 'statuses', ['is_active'])

    # Create shift_tasks table
    op.create_table(
        'shift_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('work_regime_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('shift_date', sa.Date(), nullable=False),
        sa.Column('task_name', sa.String(length=200), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('sent_to_board_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('task_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.ForeignKeyConstraint(['work_regime_id'], ['work_regimes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_shift_tasks_regime', 'shift_tasks', ['work_regime_id'])
    op.create_index('idx_shift_tasks_vehicle', 'shift_tasks', ['vehicle_id'])
    op.create_index('idx_shift_tasks_date', 'shift_tasks', ['shift_date'])
    op.create_index('idx_shift_tasks_status', 'shift_tasks', ['status'])
    op.create_index('idx_shift_tasks_priority', 'shift_tasks', [sa.text('priority DESC')])

    # Create route_tasks table
    op.create_table(
        'route_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shift_task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('route_order', sa.Integer(), nullable=False),
        sa.Column('point_a_id', sa.Integer(), nullable=False),
        sa.Column('point_b_id', sa.Integer(), nullable=False),
        sa.Column('planned_trips_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('actual_trips_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('route_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['shift_task_id'], ['shift_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('point_a_id IS NOT NULL OR point_b_id IS NOT NULL')
    )
    op.create_index('idx_route_tasks_shift_task', 'route_tasks', ['shift_task_id'])
    op.create_index('idx_route_tasks_order', 'route_tasks', ['shift_task_id', 'route_order'])
    op.create_index('idx_route_tasks_point_a', 'route_tasks', ['point_a_id'])
    op.create_index('idx_route_tasks_point_b', 'route_tasks', ['point_b_id'])


def downgrade() -> None:
    # Drop route_tasks
    op.drop_index('idx_route_tasks_point_b', table_name='route_tasks')
    op.drop_index('idx_route_tasks_point_a', table_name='route_tasks')
    op.drop_index('idx_route_tasks_order', table_name='route_tasks')
    op.drop_index('idx_route_tasks_shift_task', table_name='route_tasks')
    op.drop_table('route_tasks')

    # Drop shift_tasks
    op.drop_index('idx_shift_tasks_priority', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_status', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_date', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_vehicle', table_name='shift_tasks')
    op.drop_index('idx_shift_tasks_regime', table_name='shift_tasks')
    op.drop_table('shift_tasks')

    # Drop statuses
    op.drop_index('idx_statuses_active', table_name='statuses')
    op.drop_index('idx_statuses_category', table_name='statuses')
    op.drop_index('idx_statuses_enterprise', table_name='statuses')
    op.drop_table('statuses')

    # Drop vehicles
    op.drop_index('idx_vehicles_active', table_name='vehicles')
    op.drop_index('idx_vehicles_status', table_name='vehicles')
    op.drop_index('idx_vehicles_type', table_name='vehicles')
    op.drop_index('idx_vehicles_enterprise', table_name='vehicles')
    op.drop_table('vehicles')

    # Drop work_regimes
    op.drop_index('idx_work_regimes_active', table_name='work_regimes')
    op.drop_index('idx_work_regimes_enterprise', table_name='work_regimes')
    op.drop_table('work_regimes')

    # Drop enterprise_settings
    op.drop_table('enterprise_settings')
