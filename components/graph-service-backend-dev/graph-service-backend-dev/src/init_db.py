#!/usr/bin/env python3
"""Инициализация БД для graph-service.
Этот скрипт запускает миграции Alembic для создания таблиц.
"""

import logging

from alembic import command
from alembic.config import Config
from loguru import logger

from config.settings import get_settings

settings = get_settings()

DATABASE_URL = settings.database_url


def run_migrations():
    """Запустить миграции Alembic."""
    try:
        alembic_cfg = Config("alembic.ini")
        # Устанавливаем URL базы данных
        database_url = DATABASE_URL
        logger.info(f"Database URL (original): {database_url[:50]}...")

        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        elif not database_url.startswith("postgresql://"):
            logger.warning(f"Unexpected database URL format: {database_url[:50]}...")

        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        logger.info(f"Database URL (for migrations): {database_url[:50]}...")

        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("All migrations applied successfully!")
    except Exception as e:
        logger.exception(f"Failed to run migrations: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
