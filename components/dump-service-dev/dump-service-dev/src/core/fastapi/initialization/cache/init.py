"""Cache initialization."""

from src.core.cache import Cache


def init_cache(redis_url: str) -> None:
    """Инициализация cache."""
    Cache.init(redis_url=redis_url)
