"""Роутеры для tasks (route_tasks и shift_tasks)."""

from fastapi import APIRouter

from app.api.routers.tasks import route_tasks, route_tasks_bulk, shift_tasks, shift_tasks_bulk

router = APIRouter()
# Главный роутер для route_tasks (объединяет основные и bulk endpoints)
router.include_router(route_tasks.router)
router.include_router(route_tasks_bulk.router)
# Главный роутер для shift_tasks (объединяет основные и bulk endpoints)
router.include_router(shift_tasks.router)
router.include_router(shift_tasks_bulk.router)

__all__ = ["router"]
