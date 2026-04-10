"""API роутер V1."""

from fastapi.routing import APIRouter

from . import minio

router = APIRouter(prefix="/v1")

router.include_router(minio.router)
