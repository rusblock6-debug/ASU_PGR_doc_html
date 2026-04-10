import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import SQLITE_DATABASE_URL, settings


DATABASE_URL = settings.DATABASE_URL
logger = logging.getLogger(__name__)

try:
    async_engine = create_async_engine(DATABASE_URL)
except ModuleNotFoundError as exc:
    if "asyncpg" not in str(exc):
        raise
    logger.warning(
        "Failed to load asyncpg for settings-bort DB driver. Falling back to SQLite (%s).",
        SQLITE_DATABASE_URL,
    )
    DATABASE_URL = SQLITE_DATABASE_URL
    async_engine = create_async_engine(DATABASE_URL)

SessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

async def get_db():
    async with SessionLocal() as db:
        yield db
