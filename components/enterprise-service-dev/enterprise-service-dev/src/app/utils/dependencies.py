"""FastAPI dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Dependency для получения async session."""
    async with AsyncSessionLocal() as session:
        yield session
