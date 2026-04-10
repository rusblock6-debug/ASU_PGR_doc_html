"""
Сервис для сохранения телеметрии в Redis Streams.
"""
import json
import time
from typing import Optional
from redis.asyncio import Redis
from loguru import logger
from app.core.config import settings
from app.core.dependencies import get_redis_client


class TelemetryStorage:
    """
    Сервис для сохранения телеметрии в Redis Streams.
    
    Сохраняет сообщения от датчиков в Redis Streams с TTL.
    Формат ключа: telemetry-service:{sensor_type}:{vehicle_id}
    """
    
    def __init__(self, redis_client: Optional[Redis] = None, ttl_seconds: int = None):
        """
        Инициализация сервиса хранения телеметрии.
        
        Args:
            redis_client: Redis клиент (если None, будет получен через get_redis_client)
            ttl_seconds: TTL для Redis Streams (если None, используется из settings)
        """
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds or settings.TELEMETRY_STREAM_TTL_SECONDS
    
    async def store_telemetry(
        self,
        vehicle_id: str,
        sensor_type: str,
        data: dict
    ) -> bool:
        """
        Сохранить телеметрию в Redis Stream.
        
        Args:
            vehicle_id: ID транспортного средства
            sensor_type: Тип датчика (speed, weight, fuel, gps, vibro)
            data: Данные телеметрии
            
        Returns:
            True если успешно сохранено, False в случае ошибки
        """
        try:
            # Получаем Redis клиент если не передан
            redis = self.redis_client or await get_redis_client()
            
            # Формируем ключ Redis Stream
            stream_key = f"telemetry-service:{sensor_type}:{vehicle_id}"
            
            # Добавляем timestamp в данные
            timestamp = time.time()
            
            # Структура записи в Stream
            entry = {
                "timestamp": str(timestamp),
                "data": json.dumps(data, default=str)
            }
            
            # Добавляем запись в Redis Stream
            stream_id = await redis.xadd(stream_key, entry)
            
            # Устанавливаем TTL для ключа Stream (обновляется при каждом добавлении)
            await redis.expire(stream_key, self.ttl_seconds)
            
            logger.debug(
                "Telemetry stored in Redis Stream",
                stream_key=stream_key,
                stream_id=stream_id,
                vehicle_id=vehicle_id,
                sensor_type=sensor_type,
                ttl_seconds=self.ttl_seconds
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to store telemetry in Redis Stream",
                vehicle_id=vehicle_id,
                sensor_type=sensor_type,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def get_stream_info(self, vehicle_id: str, sensor_type: str) -> Optional[dict]:
        """
        Получить информацию о Redis Stream (для отладки).
        
        Args:
            vehicle_id: ID транспортного средства
            sensor_type: Тип датчика
            
        Returns:
            Словарь с информацией о Stream или None при ошибке
        """
        try:
            redis = self.redis_client or await get_redis_client()
            stream_key = f"telemetry-service:{sensor_type}:{vehicle_id}"
            
            # Получаем длину Stream
            length = await redis.xlen(stream_key)
            
            # Получаем TTL
            ttl = await redis.ttl(stream_key)
            
            return {
                "stream_key": stream_key,
                "length": length,
                "ttl_seconds": ttl if ttl > 0 else None
            }
            
        except Exception as e:
            logger.error(
                "Failed to get stream info",
                vehicle_id=vehicle_id,
                sensor_type=sensor_type,
                error=str(e)
            )
            return None

