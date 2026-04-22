"""Redis клиент для cache."""

# ruff: noqa: D101, S301
# mypy: disable-error-code="no-untyped-def,type-arg,no-untyped-call"

from loguru import logger

from src.core.cache.client.redis_client import RedisClient


class RedisCacheClient(RedisClient):
    def __init__(self, redis_url: str):
        super().__init__(redis_url)

    async def delete_by_key(self, key: str) -> None:
        """Удалить все значение в redis, которые имеют значение key."""
        await self.delete(key)

    async def delete_by_invalid_key(
        self,
        invalid_mask_key: str,
        params: list[str] | None = None,
    ) -> None:
        """Удалить все значение в redis, которые имеют значение invalid key."""
        async for exist_function_key in self.redis_client.scan_iter(invalid_mask_key):
            if (params is None) or any(param in exist_function_key.decode() for param in params):
                await super().delete(exist_function_key)

    async def delete_all(self) -> None:
        """Удалить все значение в redis."""
        logger.warning("Удаление всех ключей из кеша Redis")
        await self.redis_client.flushall()
