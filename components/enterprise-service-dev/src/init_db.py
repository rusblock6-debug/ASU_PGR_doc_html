#!/usr/bin/env python3
"""Инициализация БД для enterprise-service.

Этот скрипт запускает миграции Alembic для создания таблиц.
"""

import logging

from alembic import command
from alembic.config import Config
from loguru import logger

from app.core.config import settings


def run_migrations() -> None:
    """Запустить миграции Alembic."""
    try:
        alembic_cfg = Config("alembic.ini")
        # Устанавливаем URL базы данных
        database_url = settings.DATABASE_URL
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
