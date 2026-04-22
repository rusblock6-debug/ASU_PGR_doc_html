"""
Пример использования Redis Streams от telemetry-service в enterprise-service.

Этот файл показывает, как читать телеметрию из Redis Streams, созданных telemetry-service.
"""
import json
import asyncio
from typing import Optional, Dict, List
from redis.asyncio import Redis
from loguru import logger


class TelemetryReader:
    """
    Класс для чтения телеметрии из Redis Streams.
    
    Использует Streams, созданные telemetry-service:
    - telemetry-service:{sensor_type}:{vehicle_id}
    """
    
    def __init__(self, redis_client: Redis):
        """
        Инициализация читателя телеметрии.
        
        Args:
            redis_client: Redis клиент
        """
        self.redis = redis_client
    
    async def read_telemetry(
        self,
        vehicle_id: str,
        sensor_type: str,
        count: int = 10
    ) -> List[Dict]:
        """
        Читать телеметрию из Redis Stream.
        
        Args:
            vehicle_id: ID транспортного средства (например, "4_truck")
            sensor_type: Тип датчика (speed, weight, fuel, gps, vibro)
            count: Количество записей для чтения
            
        Returns:
            Список записей телеметрии
        """
        stream_key = f"telemetry-service:{sensor_type}:{vehicle_id}"
        
        try:
            # Читаем последние записи из Stream
            entries = await self.redis.xrevrange(stream_key, count=count)
            
            result = []
            for entry_id, data in entries:
                telemetry_data = json.loads(data['data'])
                result.append({
                    "entry_id": entry_id,
                    "timestamp": float(data['timestamp']),
                    "vehicle_id": telemetry_data['metadata']['vehicle_id'],
                    "sensor_type": telemetry_data['metadata']['sensor_type'],
                    "sensor_timestamp": telemetry_data['metadata']['timestamp'],
                    "data": telemetry_data['data']
                })
            
            logger.info(
                "Telemetry read from Stream",
                stream_key=stream_key,
                count=len(result)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to read telemetry from Stream",
                stream_key=stream_key,
                error=str(e),
                exc_info=True
            )
            return []
    
    async def read_latest_telemetry(
        self,
        vehicle_id: str,
        sensor_type: str
    ) -> Optional[Dict]:
        """
        Получить последнюю запись телеметрии.
        
        Args:
            vehicle_id: ID транспортного средства
            sensor_type: Тип датчика
            
        Returns:
            Последняя запись телеметрии или None
        """
        stream_key = f"telemetry-service:{sensor_type}:{vehicle_id}"
        
        try:
            entries = await self.redis.xrevrange(stream_key, count=1)
            
            if not entries:
                return None
            
            entry_id, data = entries[0]
            telemetry_data = json.loads(data['data'])
            
            return {
                "entry_id": entry_id,
                "timestamp": float(data['timestamp']),
                "vehicle_id": telemetry_data['metadata']['vehicle_id'],
                "sensor_type": telemetry_data['metadata']['sensor_type'],
                "sensor_timestamp": telemetry_data['metadata']['timestamp'],
                "data": telemetry_data['data']
            }
            
        except Exception as e:
            logger.error(
                "Failed to read latest telemetry",
                stream_key=stream_key,
                error=str(e),
                exc_info=True
            )
            return None
    
    async def get_stream_info(
        self,
        vehicle_id: str,
        sensor_type: str
    ) -> Optional[Dict]:
        """
        Получить информацию о Stream (длина, TTL).
        
        Args:
            vehicle_id: ID транспортного средства
            sensor_type: Тип датчика
            
        Returns:
            Информация о Stream или None
        """
        stream_key = f"telemetry-service:{sensor_type}:{vehicle_id}"
        
        try:
            length = await self.redis.xlen(stream_key)
            ttl = await self.redis.ttl(stream_key)
            
            return {
                "stream_key": stream_key,
                "length": length,
                "ttl_seconds": ttl if ttl > 0 else None
            }
            
        except Exception as e:
            logger.error(
                "Failed to get stream info",
                stream_key=stream_key,
                error=str(e)
            )
            return None


# Пример использования:
async def example_usage():
    """
    Пример использования TelemetryReader.
    
    Этот код можно использовать в enterprise-service для чтения телеметрии.
    """
    from redis.asyncio import from_url
    
    # Подключение к Redis (используем тот же Redis что и telemetry-service)
    redis = await from_url("redis://redis:6379/0", decode_responses=True)
    
    # Создаем читатель телеметрии
    reader = TelemetryReader(redis)
    
    # Пример 1: Получить последнюю запись скорости
    latest_speed = await reader.read_latest_telemetry("4_truck", "speed")
    if latest_speed:
        print(f"Последняя скорость: {latest_speed['data']}")
    
    # Пример 2: Получить последние 10 записей веса
    weight_history = await reader.read_telemetry("4_truck", "weight", count=10)
    print(f"Последние 10 записей веса: {len(weight_history)} записей")
    
    # Пример 3: Получить информацию о Stream
    stream_info = await reader.get_stream_info("4_truck", "speed")
    if stream_info:
        print(f"Stream info: {stream_info}")
    
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(example_usage())

