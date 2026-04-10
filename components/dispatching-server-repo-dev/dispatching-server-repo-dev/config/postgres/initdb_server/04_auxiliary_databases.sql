-- ==============================================================================
-- AUXILIARY DATABASES INITIALIZATION
-- ==============================================================================
-- Инициализация вспомогательных баз данных для внешних сервисов.
-- 
-- Airbyte - ETL система для интеграции данных
-- Superset - BI платформа для визуализации и аналитики
-- ==============================================================================

-- ==============================================================================
-- AIRBYTE DATABASE
-- ==============================================================================

\c airbyte;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ==============================================================================
-- SUPERSET DATABASE
-- ==============================================================================

\c superset;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

