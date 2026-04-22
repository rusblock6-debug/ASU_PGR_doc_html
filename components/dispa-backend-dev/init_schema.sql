-- Initial schema for Trip Service
-- Create 6 tables + AlembicVersion + TimescaleDB hypertables

-- Создание таблицы alembic_version для отслеживания миграций
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

-- Вставка версии миграции
INSERT INTO alembic_version (version_num) VALUES ('001') ON CONFLICT DO NOTHING;

-- Создание таблицы shift_tasks
CREATE TABLE IF NOT EXISTS shift_tasks (
    shift_id VARCHAR(255) PRIMARY KEY,
    tasks_data JSONB NOT NULL,
    server_timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_shift_tasks_status ON shift_tasks(status);
CREATE INDEX IF NOT EXISTS ix_shift_tasks_status_created ON shift_tasks(status, created_at);

-- Создание таблицы tasks
CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(255) PRIMARY KEY,
    shift_id VARCHAR(255) NOT NULL,
    start_point_id VARCHAR(255) NOT NULL,
    stop_point_id VARCHAR(255) NOT NULL,
    "order" INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    extra_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_shift_task UNIQUE (shift_id, task_id)
);

CREATE INDEX IF NOT EXISTS ix_tasks_shift_id ON tasks(shift_id);
CREATE INDEX IF NOT EXISTS ix_tasks_start_point_id ON tasks(start_point_id);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS ix_tasks_shift_order ON tasks(shift_id, "order");
CREATE INDEX IF NOT EXISTS ix_tasks_status_start_point ON tasks(status, start_point_id);

-- Создание таблицы trips
CREATE TABLE IF NOT EXISTS trips (
    internal_trip_id VARCHAR(50) PRIMARY KEY,
    vehicle_id VARCHAR(100) NOT NULL,
    task_id VARCHAR(255),
    trip_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    loading_point_id VARCHAR(255),
    loading_tag VARCHAR(255),
    loading_timestamp TIMESTAMPTZ,
    unloading_point_id VARCHAR(255),
    unloading_tag VARCHAR(255),
    unloading_timestamp TIMESTAMPTZ,
    extra_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_trips_vehicle_id ON trips(vehicle_id);
CREATE INDEX IF NOT EXISTS ix_trips_trip_type ON trips(trip_type);
CREATE INDEX IF NOT EXISTS ix_trips_task_id ON trips(task_id);
CREATE INDEX IF NOT EXISTS ix_trips_vehicle_created ON trips(vehicle_id, created_at);
CREATE INDEX IF NOT EXISTS ix_trips_type_created ON trips(trip_type, created_at);

-- Создание таблицы trip_state_history
CREATE TABLE IF NOT EXISTS trip_state_history (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL,
    vehicle_id VARCHAR(100) NOT NULL,
    internal_trip_id VARCHAR(50),
    state VARCHAR(50) NOT NULL,
    state_data JSONB NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,
    trigger_data JSONB
);

CREATE INDEX IF NOT EXISTS ix_trip_state_history_timestamp ON trip_state_history("timestamp");
CREATE INDEX IF NOT EXISTS ix_trip_state_history_vehicle_id ON trip_state_history(vehicle_id);
CREATE INDEX IF NOT EXISTS ix_trip_state_history_vehicle_timestamp ON trip_state_history(vehicle_id, "timestamp");
CREATE INDEX IF NOT EXISTS ix_trip_state_history_trip_timestamp ON trip_state_history(internal_trip_id, "timestamp");

-- Создание таблицы trip_tag_history
CREATE TABLE IF NOT EXISTS trip_tag_history (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL,
    vehicle_id VARCHAR(100) NOT NULL,
    internal_trip_id VARCHAR(50),
    point_id VARCHAR(255) NOT NULL,
    tag VARCHAR(255) NOT NULL,
    extra_data JSONB
);

CREATE INDEX IF NOT EXISTS ix_trip_tag_history_timestamp ON trip_tag_history("timestamp");
CREATE INDEX IF NOT EXISTS ix_trip_tag_history_vehicle_id ON trip_tag_history(vehicle_id);
CREATE INDEX IF NOT EXISTS ix_trip_tag_history_vehicle_timestamp ON trip_tag_history(vehicle_id, "timestamp");
CREATE INDEX IF NOT EXISTS ix_trip_tag_history_trip_timestamp ON trip_tag_history(internal_trip_id, "timestamp");
CREATE INDEX IF NOT EXISTS ix_trip_tag_history_point_id ON trip_tag_history(point_id);

-- Создание таблицы trip_analytics
CREATE TABLE IF NOT EXISTS trip_analytics (
    id SERIAL PRIMARY KEY,
    internal_trip_id VARCHAR(50) NOT NULL UNIQUE,
    vehicle_id VARCHAR(100) NOT NULL,
    total_duration_seconds FLOAT,
    moving_empty_duration_seconds FLOAT,
    stopped_empty_duration_seconds FLOAT,
    loading_duration_seconds FLOAT,
    moving_loaded_duration_seconds FLOAT,
    stopped_loaded_duration_seconds FLOAT,
    unloading_duration_seconds FLOAT,
    state_transitions_count INTEGER,
    analytics_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_trip_analytics_internal_trip_id ON trip_analytics(internal_trip_id);
CREATE INDEX IF NOT EXISTS ix_trip_analytics_vehicle_id ON trip_analytics(vehicle_id);
CREATE INDEX IF NOT EXISTS ix_trip_analytics_vehicle_created ON trip_analytics(vehicle_id, created_at);

-- Создание TimescaleDB hypertables
SELECT create_hypertable(
    'trips',
    'created_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'trip_state_history',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'trip_tag_history',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'trip_analytics',
    'created_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);
