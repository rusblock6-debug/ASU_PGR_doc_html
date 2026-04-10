"""
Конфигурация SQLAlchemy engine и session.
"""
from collections.abc import AsyncGenerator
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine, autocommit=False, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Dependency для получения async session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e

Session = Annotated[AsyncSession, Depends(get_db)]