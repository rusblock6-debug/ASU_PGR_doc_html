-- Создание базы данных для enterprise-service
-- Этот скрипт выполняется ТОЛЬКО в docker-compose.server.yaml
SELECT 'CREATE DATABASE enterprise_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'enterprise_db')\gexec

-- Подключение к enterprise_db и выдача прав
\c enterprise_db
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON DATABASE enterprise_db TO postgres;
