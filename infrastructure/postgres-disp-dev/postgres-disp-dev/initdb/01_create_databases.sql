-- Создание дополнительной базы данных для graph-service
-- База dispatching создается автоматически через POSTGRES_DB
SELECT 'CREATE DATABASE dispatching_graph' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dispatching_graph')\gexec

-- База данных для Airbyte ETL
SELECT 'CREATE DATABASE airbyte'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airbyte')\gexec

-- База данных для Superset BI
SELECT 'CREATE DATABASE superset'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'superset')\gexec
