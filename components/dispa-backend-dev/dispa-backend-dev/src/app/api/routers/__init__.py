"""FastAPI роутеры для API endpoints."""

from fastapi import APIRouter

from .active import router as active_router
from .cycle_state_history import router as cycle_state_history_router
from .event_log import router as event_log_router
from .events import router as events_router
from .fleet_control import router as fleet_control_router
from .health import router as health_router
from .history import router as history_router
from .server import router as server_router
from .state import router as state_router
from .tasks import route_tasks_router, shift_tasks_router
from .trips import router as trips_router

api_router = APIRouter(prefix="/api")

api_router.include_router(
    shift_tasks_router,
)
api_router.include_router(route_tasks_router)
api_router.include_router(trips_router)
api_router.include_router(state_router)
api_router.include_router(active_router)
api_router.include_router(event_log_router)
api_router.include_router(server_router, prefix="/server")
api_router.include_router(cycle_state_history_router, prefix="/cycle-state-history")
api_router.include_router(history_router, tags=["External"])
api_router.include_router(fleet_control_router)

# SSE для real-time обновлений
api_router.include_router(events_router)

__all__ = [
    "api_router",
    "health_router",
]
