"""Настройка async SQLAlchemy engine и session factory."""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import settings

_url = settings.distributor.POSTGRES_URL
if _url is None:
    raise RuntimeError(
        "Distributor DB not configured (DISTRIBUTOR__POSTGRES_HOST is required)",
    )

# asyncpg URL: postgresql+asyncpg://...
DATABASE_URL = _url.replace("postgresql://", "postgresql+asyncpg://", 1)

async_engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=0,
)

async_session_factory = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)
