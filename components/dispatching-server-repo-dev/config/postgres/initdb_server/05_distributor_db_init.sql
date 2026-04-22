-- Создание базы данных для cdc-distributor
-- Этот скрипт выполняется ТОЛЬКО в docker-compose.server.yaml
SELECT 'CREATE DATABASE distributor'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'distributor')\gexec

-- Подключение к distributor и выдача прав
\c distributor
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON DATABASE distributor TO postgres;
