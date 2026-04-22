from typing import Optional
import logging
import redis.asyncio as redis
from fastapi.security import OAuth2PasswordBearer
from app.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

logger = logging.getLogger(__name__)

class RedisClient:
    """Async Redis клиент"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding='utf-8',
            )
            await self.redis.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Redis connection failed {str(e)}")
            raise

    async def disconnect(self) -> None:
        try:
            if self.redis:
                await self.redis.close()
                logger.info("Redis disconnected successfully")
        except Exception as e:
            logger.error(f"Redis connection failed {str(e)}")

    async def add_to_blacklist(self, token: str, expiration: int = 3600) -> None:
        """Добавить токен в черный список"""
        try:
            if self.redis:
                await self.redis.setex(f"blacklisted_token:{token}", expiration, "true")
                logger.info(f"Token added to blacklist: {token}")
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {str(e)}")

    async def is_token_blacklisted(self, token: str) -> bool:
        """Проверить, находится ли токен в черном списке"""
        try:
            if self.redis:
                exists = await self.redis.exists(f"blacklisted_token:{token}")
                return exists == 1
            return False
        except Exception as e:
            logger.error(f"Failed to check if token is blacklisted: {str(e)}")
            return False

redis_client = RedisClient()
