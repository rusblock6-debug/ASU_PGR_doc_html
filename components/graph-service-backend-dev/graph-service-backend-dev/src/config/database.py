"""Асинхронная конфигурация базы данных для graph-service (SQLAlchemy 2.x + asyncpg)"""

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings

settings = get_settings()

# Настройки подключения к PostgreSQL (async)

ASYNC_DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Асинхронный движок и фабрика сессий
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession]:
    """Зависимость FastAPI: асинхронная сессия БД."""
    async with AsyncSessionLocal() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_async_db)]


async def test_db_connection() -> bool:
    """Проверка подключения к базе данных (async).
    Note: Только проверка, объекты не создаются.
    """
    try:
        async with async_engine.connect() as connection:
            from sqlalchemy import literal_column, select

            result: Any = await connection.execute(select(literal_column("version()")))
            _ = result.scalar()
            try:
                result = await connection.execute(select(literal_column("PostGIS_Version()")))
                _ = result.scalar()
            except Exception:  # noqa: S110
                pass
            return True
    except Exception:
        return False
