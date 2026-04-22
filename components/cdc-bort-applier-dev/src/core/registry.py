"""Реестр пулов БД для DI."""

import asyncpg


class ServiceRegistry:
    """Registry for a single service/database with its dependencies."""

    def __init__(self, name: str, pool: asyncpg.Pool):
        self.name = name
        self._pool = pool

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the database pool."""
        return self._pool

    async def close(self) -> None:
        """Close the pool."""
        await self._pool.close()
