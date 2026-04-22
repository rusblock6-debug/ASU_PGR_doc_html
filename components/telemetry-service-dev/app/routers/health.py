"""
Health check endpoints.
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from loguru import logger
from app.core.dependencies import get_redis_client
from typing import Optional
from app.services.mqtt_client import TelemetryMQTTClient

router = APIRouter(prefix="/health", tags=["health"])

# Глобальная переменная для проверки состояния MQTT клиента
mqtt_client_instance: Optional[TelemetryMQTTClient] = None


@router.get("")
async def health_check():
    """
    Базовая проверка здоровья приложения.
    """
    return {"status": "ok", "service": "telemetry-service"}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe - процесс жив.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe - сервис готов обрабатывать запросы.
    
    Проверяет подключение к Redis и MQTT брокеру.
    """
    checks = {
        "redis": False,
        "mqtt": False
    }
    
    # Проверка Redis
    try:
        redis = await get_redis_client()
        await redis.ping()
        checks["redis"] = True
    except Exception as e:
        logger.warning("Redis health check failed", error=str(e))
    
    # Проверка MQTT
    try:
        if mqtt_client_instance and mqtt_client_instance.is_connected():
            checks["mqtt"] = True
        else:
            logger.warning("MQTT client not connected")
    except Exception as e:
        logger.warning("MQTT health check failed", error=str(e))
    
    # Если все проверки пройдены
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    
    # Если хотя бы одна проверка не пройдена
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not ready", "checks": checks}
    )

