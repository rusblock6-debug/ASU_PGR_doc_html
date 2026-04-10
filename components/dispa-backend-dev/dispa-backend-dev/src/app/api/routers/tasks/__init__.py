"""Роутеры для tasks (route_tasks и shift_tasks)."""

from fastapi import APIRouter

from app.api.routers.tasks import route_tasks, route_tasks_bulk, shift_tasks, shift_tasks_bulk

# Главный роутер для route_tasks (объединяет основные и bulk endpoints)
route_tasks_router = APIRouter(prefix="", tags=["tasks"])
route_tasks_router.include_router(route_tasks.router)
route_tasks_router.include_router(route_tasks_bulk.router)

# Главный роутер для shift_tasks (объединяет основные и bulk endpoints)
shift_tasks_router = APIRouter(prefix="", tags=["shift-tasks"])
shift_tasks_router.include_router(shift_tasks.router)
shift_tasks_router.include_router(shift_tasks_bulk.router)
