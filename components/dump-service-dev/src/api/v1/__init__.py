"""API роутер V1."""

from fastapi.routing import APIRouter

from . import file, trip_service_dump

router = APIRouter(prefix="/v1")

router.include_router(trip_service_dump.router)
router.include_router(file.router)
