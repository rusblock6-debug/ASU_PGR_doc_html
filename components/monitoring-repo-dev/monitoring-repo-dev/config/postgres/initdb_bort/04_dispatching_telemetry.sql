-- ==============================================================================
-- DISPATCHING DATABASE - Telemetry Infrastructure
-- ==============================================================================
-- Создание infrastructure таблицы для телеметрии в БД dispatching.
--
-- Таблица mqtt_raw_data используется eKuiper для архивного хранения
-- ВСЕХ MQTT сообщений со всех топиков.
--
-- Используется eKuiper правилом mqtt_raw_to_jsonb.
--
-- ==============================================================================

-- Подключение к БД dispatching
\c dispatching;

-- ==============================================================================
-- EXTENSIONS
-- ==============================================================================


-- TimescaleDB extension - для hypertable mqtt_raw_data
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- UUID extension - для генерации UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- SCHEMA CREATION
-- ==============================================================================

-- Telemetry schema - для телеметрических данных от eKuiper
CREATE SCHEMA IF NOT EXISTS telemetry;

-- ==============================================================================
-- GRANTS - Права для postgres пользователя
-- ==============================================================================

-- Public schema - права для создания таблиц через Alembic
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Telemetry schema - права для телеметрических данных
GRANT ALL PRIVILEGES ON SCHEMA telemetry TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA telemetry TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA telemetry TO postgres;

-- ==============================================================================
-- TELEMETRY TABLE - MQTT Raw Data Archive
-- ==============================================================================

-- Таблица для архивного хранения ВСЕХ MQTT сообщений
CREATE TABLE IF NOT EXISTS telemetry.mqtt_raw_data (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    topic TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, time)
);

-- ==============================================================================
-- TIMESCALEDB HYPERTABLE
-- ==============================================================================

-- Конвертируем в TimescaleDB hypertable для автоматического партиционирования
-- Партиционирование по времени (1-day chunks)
SELECT create_hypertable(
    'telemetry.mqtt_raw_data',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ==============================================================================
-- INDEXES
-- ==============================================================================

-- Индекс для поиска по топику и времени
CREATE INDEX IF NOT EXISTS idx_mqtt_raw_data_topic 
ON telemetry.mqtt_raw_data (topic, time DESC);

-- GIN индекс для поиска в JSONB payload
CREATE INDEX IF NOT EXISTS idx_mqtt_raw_data_payload 
ON telemetry.mqtt_raw_data USING GIN (raw_payload);

-- Индекс для фильтрации необработанных сообщений
CREATE INDEX IF NOT EXISTS idx_mqtt_raw_data_processed 
ON telemetry.mqtt_raw_data (processed, time DESC) 
WHERE processed = FALSE;

-- ==============================================================================
-- RETENTION POLICY
-- ==============================================================================

-- Автоматическая очистка данных старше 30 дней
-- TimescaleDB автоматически удалит старые chunks
SELECT add_retention_policy(
    'telemetry.mqtt_raw_data',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

-- ==============================================================================
-- COMMENTS
-- ==============================================================================

COMMENT ON TABLE telemetry.mqtt_raw_data IS 
'Архивное хранение ВСЕХ MQTT сообщений. Используется eKuiper для записи raw данных всех топиков. TimescaleDB hypertable с retention policy 30 дней.';

COMMENT ON COLUMN telemetry.mqtt_raw_data.time IS 
'Timestamp получения сообщения (используется для партиционирования)';

COMMENT ON COLUMN telemetry.mqtt_raw_data.topic IS 
'MQTT топик источника сообщения';

COMMENT ON COLUMN telemetry.mqtt_raw_data.raw_payload IS 
'Полное сообщение в JSONB формате';

COMMENT ON COLUMN telemetry.mqtt_raw_data.processed IS 
'Флаг обработки сообщения (для повторной обработки)';

