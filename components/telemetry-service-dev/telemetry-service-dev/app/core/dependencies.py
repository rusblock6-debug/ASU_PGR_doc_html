"""
Зависимости для FastAPI приложения.
"""
from typing import Optional
from redis.asyncio import Redis
from redis.asyncio import from_url
from loguru import logger
from app.core.config import settings

# Глобальный экземпляр Redis клиента
redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """
    Получить Redis клиент для работы с базами данных.
    
    Returns:
        Redis клиент
    """
    global redis_client
    
    if redis_client is None:
        logger.info("Creating Redis connection", url=settings.REDIS_URL)
        redis_client = await from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    return redis_client


async def close_redis_client():
    """
    Закрыть соединение с Redis.
    """
    global redis_client
    
    if redis_client:
        logger.info("Closing Redis connection")
        await redis_client.close()
        redis_client = None

