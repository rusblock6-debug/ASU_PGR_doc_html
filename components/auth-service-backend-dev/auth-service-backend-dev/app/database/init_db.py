#!/usr/bin/env python3
"""
Инициализация БД для enterprise-service.
Этот скрипт запускает миграции Alembic для создания таблиц.
"""
from alembic import command
from alembic.config import Config
from app.config import settings
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.services.permission import get_permission_names, create_permissions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_migrations():
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


def read_permissions_from_json(file_path: str = "permissions.json") -> list:
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        logger.info(f"Файл {file_path} не найден")
        return []
    try:
        with open(file_path_obj, 'r', encoding='utf-8') as file:
            permission_data = json.load(file)

        return list(permission_data.values()) if permission_data else []

    except json.JSONDecodeError:
        logger.error(f"Ошибка при парсинге JSON в файле {file_path}")
        return []

    except Exception as e:
        logger.error(f"Произошла ошибка при чтения файла: {e}")
        return []


async def get_missing_roles_from_db(db: AsyncSession):
    db_permissions = set(await get_permission_names(db))
    json_permissions = set(read_permissions_from_json())

    missing_permissions = list(json_permissions - db_permissions)
    return missing_permissions


async def add_missing_permissions(db: AsyncSession):
    """Добавить недостающие права в БД."""
    missing_permissions = await get_missing_roles_from_db(db)

    if not missing_permissions:
        logger.info("Нет недостающих прав для добавления")
        return

    await create_permissions(db, missing_permissions)
    logger.info(f"Добавлено {len(missing_permissions)} новых прав: {missing_permissions}")
