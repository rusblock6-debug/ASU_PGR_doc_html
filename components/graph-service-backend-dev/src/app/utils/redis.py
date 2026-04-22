from typing import Any, cast

import redis
from loguru import logger

from app.middleware.logging import setup_logger
from config.settings import get_settings

settings = get_settings()

setup_logger()


class Singleton(type):
    _instances: dict[type, Any] = {}

    def __call__(cls, *args, **kwargs) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Cache(metaclass=Singleton):
    def __init__(self) -> None:
        self.pool: redis.ConnectionPool = redis.ConnectionPool(
            host=settings.redis.redis_host,
            port=int(settings.redis.redis_port),
            db=settings.redis.cache_db,
        )
        self._redis: redis.Redis | None = None

    def close(self) -> None:
        if self._redis:
            self._redis.close()

    @property
    def redis(self) -> redis.Redis:
        if not self._redis:
            self.get_connection()
        return cast(redis.Redis, self._redis)

    def get_connection(self) -> None:
        self._redis = redis.Redis(connection_pool=self.pool)

    def dict_get_all(self, key_prefix: str) -> dict[str, Any]:
        """Получить все hash по ключам, начинающимся с key_prefix. Возвращает {key: dict, ...}."""
        pattern = f"{key_prefix}*"
        keys = self.redis.keys(pattern)
        result = {}
        for k in keys:  # type: ignore[union-attr]
            key_str = k.decode() if isinstance(k, bytes) else k
            val = self.dict_get(key_str)
            if val is not None:
                result[key_str] = val
        return result

    def dict_get(self, key: str) -> Any:
        """Получить весь hash по ключу. Возвращает dict или None, если ключа нет."""
        raw = self.redis.hgetall(key)  # type: ignore[union-attr]
        if not raw:
            return None
        result = {}
        for k, v in raw.items():  # type: ignore[union-attr]
            k_str = k.decode() if isinstance(k, bytes) else k
            v_str = v.decode() if isinstance(v, bytes) else str(v)
            try:
                result[k_str] = float(v_str)
            except ValueError:
                result[k_str] = v_str  # type: ignore[assignment]
        return result

    def dict_set(self, key: str, value: Any) -> bool | None:
        if not isinstance(value, dict):
            raise TypeError("dict_set value must be a dict")
        mapping = {k: str(v) for k, v in value.items()}
        logger.debug(f"Setting {key} to {mapping}")
        self.redis.hset(key, mapping=mapping)
        return True

    def get(self, key: str) -> Any:
        return self.redis.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool | None:
        logger.debug(f"Setting {key} to {value}")
        return self.redis.set(key, value, ex=ttl)  # type: ignore[return-value]

    def incr(self, key: str, amount: int = 1) -> int:
        return self.redis.incr(key, amount=amount)  # type: ignore[return-value]

    def delete(self, key: str) -> int:
        logger.debug(f"Deleting {key}")
        return self.redis.delete(key)  # type: ignore[return-value]

    def clean_by_key(self, key: str) -> None:
        keys = self.redis.keys(f"{key}*")  # type: ignore[union-attr]
        for key in keys:  # type: ignore[union-attr]
            self.redis.delete(key)


cache = Cache()
