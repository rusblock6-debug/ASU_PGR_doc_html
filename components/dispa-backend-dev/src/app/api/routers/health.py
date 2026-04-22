"""Эндпоинты проверки здоровья сервиса (health, liveness, readiness)."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"], prefix="/health")


@router.get("")
async def health_check() -> dict[str, str]:
    """Базовая проверка здоровья сервиса."""
    return {"status": "ok", "service": "trip-service", "version": "1.0.0"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe — процесс жив."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Kubernetes readiness probe — сервис готов принимать запросы."""
    # TODO: Проверить подключения к Redis, PostgreSQL, MQTT
    return {"status": "ready"}
