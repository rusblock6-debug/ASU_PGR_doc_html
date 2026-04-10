"""Главый API роутер."""

from fastapi.routing import APIRouter

from src.api.rest import v1

main_router = APIRouter(prefix="/api")

main_router.include_router(router=v1.router)

__all__ = ["main_router"]
