"""Initial schema - создание всех таблиц с нуля.

Включает:
- shift_tasks: Задания на смену от enterprise-service
- route_tasks: Маршрутные задания
- cycles: Циклы работы техники
- trips: Рейсы (наследуется от cycles через JTI)
- cycle_state_history: История состояний State Machine
- cycle_tag_history: История меток локации
- cycle_analytics: Аналитические метрики циклов

Все таблицы создаются с point_id как String(255).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from loguru import logger


# Ревизия Alembic.
revision = "000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Миграция вверх: создание всех таблиц (идемпотентная)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # 1. Создание таблицы shift_tasks
    if 'shift_tasks' not in existing_tables:
        op.create_table(
            'shift_tasks',
            sa.Column('id', sa.String(255), nullable=False),
            sa.Column('work_regime_id', sa.Integer(), nullable=False),
            sa.Column('vehicle_id', sa.Integer(), nullable=False),
            sa.Column('shift_date', sa.String(50), nullable=False),
            sa.Column('task_name', sa.String(500), nullable=False),
            sa.Column('priority', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
            sa.Column('sent_to_board_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('task_data', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_shift_tasks_work_regime_id', 'shift_tasks', ['work_regime_id'])
        op.create_index('ix_shift_tasks_vehicle_id', 'shift_tasks', ['vehicle_id'])
        op.create_index('ix_shift_tasks_status', 'shift_tasks', ['status'])
        op.create_index('ix_shift_tasks_status_created', 'shift_tasks', ['status', 'created_at'])
        op.create_index('ix_shift_tasks_vehicle_date', 'shift_tasks', ['vehicle_id', 'shift_date'])
        logger.info("Table 'shift_tasks' created")
    else:
        logger.warning("Table 'shift_tasks' already exists - skipping")
    
    # 2. Создание таблицы route_tasks (point_a_id и point_b_id - строки!)
    if 'route_tasks' not in existing_tables:
        op.create_table(
            'route_tasks',
            sa.Column('id', sa.String(255), nullable=False),
            sa.Column('shift_task_id', sa.String(255), nullable=False),
            sa.Column('route_order', sa.Integer(), nullable=False),
            sa.Column('point_a_id', sa.String(255), nullable=False),
            sa.Column('point_b_id', sa.String(255), nullable=False),
            sa.Column('planned_trips_count', sa.Integer(), nullable=True, server_default='1'),
            sa.Column('actual_trips_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
            sa.Column('route_data', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['shift_task_id'], ['shift_tasks.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('shift_task_id', 'id', name='uq_shift_route_task')
        )
        op.create_index('ix_route_tasks_shift_task_id', 'route_tasks', ['shift_task_id'])
        op.create_index('ix_route_tasks_point_a_id', 'route_tasks', ['point_a_id'])
        op.create_index('ix_route_tasks_status', 'route_tasks', ['status'])
        op.create_index('ix_route_tasks_shift_order', 'route_tasks', ['shift_task_id', 'route_order'])
        op.create_index('ix_route_tasks_status_point_a', 'route_tasks', ['status', 'point_a_id'])
        logger.info("SUCCESS: Table 'route_tasks' created")
    else:
        logger.info("WARNING:  Table 'route_tasks' already exists - skipping")
        
        # Если таблица существует, проверяем и обновляем типы колонок point_a_id и point_b_id
        columns = {col['name']: col for col in inspector.get_columns('route_tasks')}
        
        if 'point_a_id' in columns:
            col_type = str(columns['point_a_id']['type'])
            if 'INTEGER' in col_type.upper() or 'INT' in col_type.upper():
                op.execute("ALTER TABLE route_tasks ALTER COLUMN point_a_id TYPE VARCHAR(255) USING point_a_id::VARCHAR")
                logger.info("SUCCESS: Column 'point_a_id' changed to VARCHAR(255)")
        
        if 'point_b_id' in columns:
            col_type = str(columns['point_b_id']['type'])
            if 'INTEGER' in col_type.upper() or 'INT' in col_type.upper():
                op.execute("ALTER TABLE route_tasks ALTER COLUMN point_b_id TYPE VARCHAR(255) USING point_b_id::VARCHAR")
                logger.info("SUCCESS: Column 'point_b_id' changed to VARCHAR(255)")
    
    # 3. Создание таблицы cycles (включая поле source)
    if 'cycles' not in existing_tables:
        op.create_table(
            'cycles',
            sa.Column('cycle_id', sa.String(50), nullable=False),
            sa.Column('vehicle_id', sa.String(100), nullable=False),
            sa.Column('task_id', sa.String(255), nullable=True),
            sa.Column('shift_id', sa.String(255), nullable=True),
            sa.Column('from_point_id', sa.String(255), nullable=True),
            sa.Column('to_point_id', sa.String(255), nullable=True),
            sa.Column('cycle_started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cycle_completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('source', sa.String(50), nullable=False, server_default='system'),
            sa.Column('cycle_status', sa.String(50), nullable=False, server_default='in_progress'),
            sa.Column('cycle_type', sa.String(50), nullable=False, server_default='normal'),
            sa.Column('entity_type', sa.String(50), nullable=False, server_default='cycle'),
            sa.Column('extra_data', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.PrimaryKeyConstraint('cycle_id')
        )
        op.create_index('ix_cycles_vehicle_id', 'cycles', ['vehicle_id'])
        op.create_index('ix_cycles_cycle_status', 'cycles', ['cycle_status'])
        op.create_index('ix_cycles_source', 'cycles', ['source'])
        op.create_index('ix_cycles_cycle_type', 'cycles', ['cycle_type'])
        op.create_index('ix_cycles_vehicle_created', 'cycles', ['vehicle_id', 'created_at'])
        op.create_index('ix_cycles_status_created', 'cycles', ['cycle_status', 'created_at'])
        op.create_index('ix_cycles_task_id', 'cycles', ['task_id'])
        op.create_index('ix_cycles_type', 'cycles', ['cycle_type'])
        logger.info("SUCCESS: Table 'cycles' created")
    else:
        logger.info("WARNING:  Table 'cycles' already exists - skipping")
        
        # Если таблица существует, проверяем наличие колонки source
        columns = [col['name'] for col in inspector.get_columns('cycles')]
        if 'source' not in columns:
            op.add_column(
                "cycles",
                sa.Column(
                    "source",
                    sa.String(50),
                    nullable=False,
                    server_default="system",
                ),
            )
            op.create_index("ix_cycles_source", "cycles", ["source"])
            logger.info("SUCCESS: Column 'source' added to 'cycles' table")
    
    # 4. Создание таблицы trips (наследуется от cycles через JTI, включая cycle_num)
    if 'trips' not in existing_tables:
        op.create_table(
            'trips',
            sa.Column('cycle_id', sa.String(50), nullable=False),
            sa.Column('cycle_num', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('trip_type', sa.String(50), nullable=False),
            sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('loading_point_id', sa.String(255), nullable=True),
            sa.Column('loading_tag', sa.String(255), nullable=True),
            sa.Column('loading_timestamp', sa.DateTime(timezone=True), nullable=True),
            sa.Column('unloading_point_id', sa.String(255), nullable=True),
            sa.Column('unloading_tag', sa.String(255), nullable=True),
            sa.Column('unloading_timestamp', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('cycle_id'),
            sa.ForeignKeyConstraint(['cycle_id'], ['cycles.cycle_id'])
        )
        op.create_index('ix_trips_trip_type', 'trips', ['trip_type'])
        logger.info("SUCCESS: Table 'trips' created")
    else:
        logger.info("WARNING:  Table 'trips' already exists - skipping")
        
        # Если таблица существует, проверяем наличие колонки cycle_num
        columns = [col['name'] for col in inspector.get_columns('trips')]
        if 'cycle_num' not in columns:
            op.add_column(
                "trips",
                sa.Column(
                    "cycle_num",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                ),
            )
            op.execute("UPDATE trips SET cycle_num = 1 WHERE cycle_num IS NULL")
            op.alter_column("trips", "cycle_num", server_default=None)
            logger.info("SUCCESS: Column 'cycle_num' added to 'trips' table")
    
    # 5. Создание таблицы cycle_state_history
    if 'cycle_state_history' not in existing_tables:
        op.create_table(
            'cycle_state_history',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('vehicle_id', sa.String(100), nullable=False),
            sa.Column('cycle_id', sa.String(50), nullable=True),
            sa.Column('state', sa.String(50), nullable=False),
            sa.Column('state_data', JSONB, nullable=False),
            sa.Column('trigger_type', sa.String(50), nullable=False),
            sa.Column('trigger_data', JSONB, nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_cycle_state_history_timestamp', 'cycle_state_history', ['timestamp'])
        op.create_index('ix_cycle_state_history_vehicle_id', 'cycle_state_history', ['vehicle_id'])
        op.create_index('ix_cycle_state_history_vehicle_timestamp', 'cycle_state_history', ['vehicle_id', 'timestamp'])
        op.create_index('ix_cycle_state_history_cycle_timestamp', 'cycle_state_history', ['cycle_id', 'timestamp'])
        logger.info("SUCCESS: Table 'cycle_state_history' created")
    else:
        logger.info("WARNING:  Table 'cycle_state_history' already exists - skipping")
    
    # 6. Создание таблицы cycle_tag_history (point_id - строка!)
    if 'cycle_tag_history' not in existing_tables:
        op.create_table(
            'cycle_tag_history',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('vehicle_id', sa.String(100), nullable=False),
            sa.Column('cycle_id', sa.String(50), nullable=True),
            sa.Column('point_id', sa.String(255), nullable=False),
            sa.Column('tag', sa.String(255), nullable=False),
            sa.Column('extra_data', JSONB, nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_cycle_tag_history_timestamp', 'cycle_tag_history', ['timestamp'])
        op.create_index('ix_cycle_tag_history_vehicle_id', 'cycle_tag_history', ['vehicle_id'])
        op.create_index('ix_cycle_tag_history_vehicle_timestamp', 'cycle_tag_history', ['vehicle_id', 'timestamp'])
        op.create_index('ix_cycle_tag_history_cycle_timestamp', 'cycle_tag_history', ['cycle_id', 'timestamp'])
        op.create_index('ix_cycle_tag_history_point_id', 'cycle_tag_history', ['point_id'])
        logger.info("SUCCESS: Table 'cycle_tag_history' created")
    else:
        logger.info("WARNING:  Table 'cycle_tag_history' already exists - skipping")
    
    # 7. Создание таблицы cycle_analytics (from_point_id и to_point_id - строки!)
    if 'cycle_analytics' not in existing_tables:
        op.create_table(
            'cycle_analytics',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('cycle_id', sa.String(50), nullable=False),
            sa.Column('vehicle_id', sa.String(100), nullable=False),
            sa.Column('shift_id', sa.String(255), nullable=True),
            sa.Column('cycle_type', sa.String(50), nullable=True),
            sa.Column('cycle_status', sa.String(50), nullable=True),
            sa.Column('trip_type', sa.String(50), nullable=True),
            sa.Column('trip_status', sa.String(50), nullable=True),
            sa.Column('from_point_id', sa.String(255), nullable=True),
            sa.Column('to_point_id', sa.String(255), nullable=True),
            sa.Column('cycle_started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cycle_completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('trip_started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('trip_completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('total_duration_seconds', sa.Float(), nullable=True),
            sa.Column('moving_empty_duration_seconds', sa.Float(), nullable=True),
            sa.Column('stopped_empty_duration_seconds', sa.Float(), nullable=True),
            sa.Column('loading_duration_seconds', sa.Float(), nullable=True),
            sa.Column('moving_loaded_duration_seconds', sa.Float(), nullable=True),
            sa.Column('stopped_loaded_duration_seconds', sa.Float(), nullable=True),
            sa.Column('unloading_duration_seconds', sa.Float(), nullable=True),
            sa.Column('state_transitions_count', sa.Integer(), nullable=True),
            sa.Column('analytics_data', JSONB, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('cycle_id')
        )
        op.create_index('ix_cycle_analytics_vehicle_id', 'cycle_analytics', ['vehicle_id'])
        op.create_index('ix_cycle_analytics_vehicle_created', 'cycle_analytics', ['vehicle_id', 'created_at'])
        op.create_index('ix_cycle_analytics_cycle_id', 'cycle_analytics', ['cycle_id'])
        logger.info("SUCCESS: Table 'cycle_analytics' created")
    else:
        logger.info("WARNING:  Table 'cycle_analytics' already exists - skipping")
    
    # 8. Создание TimescaleDB hypertables (если TimescaleDB доступен)
    try:
        # Проверяем наличие расширения TimescaleDB
        result = conn.execute(sa.text(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
        ))
        timescaledb_installed = result.scalar()
        
        if timescaledb_installed:
            # Проверяем, не является ли таблица уже hypertable
            def is_hypertable(table_name):
                result = conn.execute(sa.text(
                    f"SELECT EXISTS(SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = '{table_name}')"
                ))
                return result.scalar()
            
            # Создаем hypertable для cycles
            if 'cycles' in existing_tables or 'cycles' not in existing_tables:
                if not is_hypertable('cycles'):
                    conn.execute(sa.text(
                        "SELECT create_hypertable('cycles', 'created_at', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
                    ))
                    logger.info("SUCCESS: Hypertable 'cycles' created")
            
            # Создаем hypertable для cycle_state_history
            if 'cycle_state_history' in existing_tables or 'cycle_state_history' not in existing_tables:
                if not is_hypertable('cycle_state_history'):
                    conn.execute(sa.text(
                        "SELECT create_hypertable('cycle_state_history', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
                    ))
                    logger.info("SUCCESS: Hypertable 'cycle_state_history' created")
            
            # Создаем hypertable для cycle_tag_history
            if 'cycle_tag_history' in existing_tables or 'cycle_tag_history' not in existing_tables:
                if not is_hypertable('cycle_tag_history'):
                    conn.execute(sa.text(
                        "SELECT create_hypertable('cycle_tag_history', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
                    ))
                    logger.info("SUCCESS: Hypertable 'cycle_tag_history' created")
            
            # Создаем hypertable для cycle_analytics
            if 'cycle_analytics' in existing_tables or 'cycle_analytics' not in existing_tables:
                if not is_hypertable('cycle_analytics'):
                    conn.execute(sa.text(
                        "SELECT create_hypertable('cycle_analytics', 'created_at', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
                    ))
                    logger.info("SUCCESS: Hypertable 'cycle_analytics' created")
        else:
            logger.info("WARNING:  TimescaleDB extension not found - skipping hypertables creation")
    except Exception as e:
        logger.info(f"WARNING:  Could not create hypertables: {e}")


def downgrade() -> None:
    """Миграция вниз: удаление всех таблиц."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Удаляем таблицы в обратном порядке (учитываем FK)
    tables_to_drop = [
        'cycle_analytics',
        'cycle_tag_history',
        'cycle_state_history',
        'trips',
        'cycles',
        'route_tasks',
        'shift_tasks'
    ]
    
    for table_name in tables_to_drop:
        if table_name in existing_tables:
            op.drop_table(table_name)
            logger.info(f"SUCCESS: Table '{table_name}' dropped")
        else:
            logger.info(f"WARNING:  Table '{table_name}' does not exist - skipping")

