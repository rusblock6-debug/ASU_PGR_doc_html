"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, str]:
    """Базовая проверка здоровья приложения."""
    return {"status": "ok", "service": "enterprise-service"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe - процесс жив."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Kubernetes readiness probe - сервис готов обрабатывать запросы."""
    return {"status": "ready"}
