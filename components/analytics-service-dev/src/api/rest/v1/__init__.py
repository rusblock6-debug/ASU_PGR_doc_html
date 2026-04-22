"""API роутер V1."""

from fastapi.routing import APIRouter

from . import minio, trip_service, vehicle_telemetry

router = APIRouter(prefix="/v1")

router.include_router(minio.router)
router.include_router(vehicle_telemetry.router)
router.include_router(trip_service.router)


__all__ = ["router"]
