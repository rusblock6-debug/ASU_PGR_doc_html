from collections.abc import AsyncGenerator
from typing import Any

from .conection_pool import ClickHousePool, create_pool
from .session import ClickHouseSession

pool = create_pool(10)


async def get_clickhouse_session() -> AsyncGenerator[ClickHouseSession, Any]:
    """Sqlalchemy like."""
    async with pool.acquire() as clickhouse_session:
        yield ClickHouseSession(clickhouse_session)


__all__ = [
    "ClickHouseSession",
    "get_clickhouse_session",
    "ClickHousePool",
    "pool",
]
