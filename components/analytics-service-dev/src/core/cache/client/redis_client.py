# ruff: noqa: S301, D100

from typing import Any

import dill
import ujson
from redis import asyncio as redis


class RedisClient:
    """Клиент для redis базы данных.

    Используется для кеша и для общения с redis напрямую.
    """

    def __init__(self, redis_url: str) -> None:
        self.redis_client = redis.from_url(redis_url)  # type: ignore[no-untyped-call]

    @staticmethod
    def __serialise(value: Any) -> bytes | set[bytes]:
        if type(value) is dict:
            return ujson.dumps(value).encode("utf-8")
        elif type(value) is set:
            return set(dill.dumps(i) for i in value)
        else:
            return dill.dumps(value)

    @staticmethod
    def __deserialise(data: bytes) -> Any:
        try:
            return ujson.loads(data)
        except ValueError:
            try:
                return dill.loads(data)
            except dill.UnpicklingError:
                return data

    async def get(self, key: str) -> Any | None:
        """Получить значение из redis."""
        result = await self.redis_client.get(key)
        if not result:
            return None
        return self.__deserialise(result)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Установить значение в redis."""
        data = self.__serialise(value)
        await self.redis_client.set(name=key, value=data, ex=ttl)

    async def delete(self, key: str) -> None:
        """Удалить все значение в redis, которые имеют значение key."""
        await self.redis_client.delete(key)

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта.

        Returns:
            Строковое представление объекта.
        """
        return f"<{self.__class__.__name__}>"
