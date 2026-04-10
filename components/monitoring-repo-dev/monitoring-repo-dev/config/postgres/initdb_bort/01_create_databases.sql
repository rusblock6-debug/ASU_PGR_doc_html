-- Создание дополнительной базы данных для graph-service
-- База dispatching создается автоматически через POSTGRES_DB
SELECT 'CREATE DATABASE dispatching_graph' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dispatching_graph')\gexec

-- База данных для trip-service
SELECT 'CREATE DATABASE trip_service' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'trip_service')\gexec
-- Создание дополнительной базы данных для graph-service
-- База dispatching создается автоматически через POSTGRES_DB
SELECT 'CREATE DATABASE dispatching_graph' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dispatching_graph')\gexec

-- База данных для trip-service
SELECT 'CREATE DATABASE trip_service' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'trip_service')\gexec

-- База данных для Airbyte ETL
SELECT 'CREATE DATABASE airbyte'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airbyte')\gexec

-- База данных для enterprise-service
SELECT 'CREATE DATABASE enterprise_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'enterprise_db')\gexec

-- База данных для auth-service
SELECT 'CREATE DATABASE dispatching_auth' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dispatching_auth')\gexec

-- База данных для settings-bort
SELECT 'CREATE DATABASE bort_settings' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bort_settings')\gexec

-- База данных для Superset BI
SELECT 'CREATE DATABASE superset'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset')\gexec

-- База данных для Airbyte ETL
SELECT 'CREATE DATABASE airbyte'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airbyte')\gexec

-- База данных для enterprise-service
SELECT 'CREATE DATABASE enterprise_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'enterprise_db')\gexec

-- База данных для Superset BI
SELECT 'CREATE DATABASE superset'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset')\gexec
