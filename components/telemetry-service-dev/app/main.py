"""
FastAPI приложение для telemetry-service.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.dependencies import get_redis_client, close_redis_client
from app.routers import health
from app.services.mqtt_client import TelemetryMQTTClient
from app.services.telemetry_storage import TelemetryStorage

# Настройка логирования
setup_logging()

# Глобальные переменные для управления жизненным циклом
mqtt_client: TelemetryMQTTClient = None
telemetry_storage: TelemetryStorage = None


async def handle_mqtt_message(vehicle_id: str, sensor_type: str, data: dict) -> None:
    """
    Обработчик сообщений от MQTT клиента.
    
    Args:
        vehicle_id: ID транспортного средства
        sensor_type: Тип датчика
        data: Данные телеметрии
    """
    try:
        # Сохраняем телеметрию в Redis Stream
        success = await telemetry_storage.store_telemetry(
            vehicle_id=vehicle_id,
            sensor_type=sensor_type,
            data=data
        )
        
        if success:
            logger.debug(
                "Telemetry message processed",
                vehicle_id=vehicle_id,
                sensor_type=sensor_type
            )
        else:
            logger.warning(
                "Failed to store telemetry",
                vehicle_id=vehicle_id,
                sensor_type=sensor_type
            )
            
    except Exception as e:
        logger.error(
            "Error processing telemetry message",
            vehicle_id=vehicle_id,
            sensor_type=sensor_type,
            error=str(e),
            exc_info=True
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    """
    global mqtt_client, telemetry_storage
    
    # Startup
    logger.info("Application startup", service="telemetry-service")
    
    try:
        # Инициализация Redis клиента
        redis = await get_redis_client()
        await redis.ping()
        logger.info("Redis connection established")
        
        # Инициализация TelemetryStorage
        telemetry_storage = TelemetryStorage(redis_client=redis)
        
        # Инициализация MQTT клиента
        mqtt_client = TelemetryMQTTClient(
            host=settings.NANOMQ_HOST,
            port=settings.NANOMQ_MQTT_PORT,
            message_handler=handle_mqtt_message
        )
        
        # Подключение к MQTT брокеру
        await mqtt_client.connect()
        
        # Сохраняем ссылку на клиент для health check
        health.mqtt_client_instance = mqtt_client
        
        logger.info("Telemetry service started successfully")
        
    except Exception as e:
        logger.error(
            "Failed to initialize telemetry service",
            error=str(e),
            exc_info=True
        )
        raise
    
    yield
    
    # Shutdown
    logger.info("Application shutdown")
    
    try:
        # Отключение от MQTT брокера
        if mqtt_client:
            await mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
    except Exception as e:
        logger.error("Error disconnecting MQTT client", error=str(e))
    
    try:
        # Закрытие Redis соединения
        await close_redis_client()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error("Error closing Redis connection", error=str(e))


app = FastAPI(
    title="Telemetry Service",
    description="Сервис для сбора и хранения телеметрии в Redis Streams",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(health.router)


@app.get("/")
async def root():
    """
    Корневой endpoint.
    """
    return {
        "service": "telemetry-service",
        "status": "running",
        "version": "1.0.0",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )

