"""FastAPI роутеры для API endpoints."""

from fastapi import APIRouter

from . import (
    active,
    cycle_state_history,
    event_log,
    events,
    fleet_control,
    history,
    server,
    state,
    tasks,
    trips,
)
from .health import router as health_router

api_router = APIRouter(prefix="/api")

api_router.include_router(tasks.router)
api_router.include_router(trips.router)
api_router.include_router(state.router)
api_router.include_router(active.router)
api_router.include_router(event_log.router)
api_router.include_router(server.router)
api_router.include_router(cycle_state_history.router)
api_router.include_router(history.router)
api_router.include_router(fleet_control.router)

# SSE для real-time обновлений
api_router.include_router(events.router)


__all__ = [
    "api_router",
    "health_router",
]
