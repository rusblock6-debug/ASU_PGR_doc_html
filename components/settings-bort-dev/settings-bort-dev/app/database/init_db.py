#!/usr/bin/env python3
"""
Инициализация локальной SQLite БД для settings-bort.
"""
import asyncio
import logging

from app.database import async_engine
from app.database.base import Base
from app.models.runtime_config_model import RuntimeConfig  # noqa: F401
from app.models.settings_model import Settings  # noqa: F401


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def _create_tables() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_schema():
    """Создать таблицы, если их еще нет."""
    try:
        logger.info("Initializing local SQLite schema...")
        asyncio.run(_create_tables())
        logger.info("SQLite schema is ready")
    except Exception as e:
        logger.exception(f"Failed to initialize SQLite schema: {e}")
        raise
