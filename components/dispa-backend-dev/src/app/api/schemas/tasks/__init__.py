"""Re-export схем задач (route_tasks, shift_tasks) и перечислений."""

from app.api.schemas.tasks.route_tasks import (
    RouteTaskBase,
    RouteTaskCreate,
    RouteTaskResponse,
    RouteTaskUpdate,
)
from app.api.schemas.tasks.route_tasks_bulk import (
    RouteTaskBulkCreateItem,
    RouteTaskBulkUpdateItem,
    RouteTaskBulkUpsertItem,
    RouteTaskBulkUpsertRequest,
    RouteTaskBulkUpsertResponse,
)
from app.api.schemas.tasks.shift_tasks import (
    ShiftTaskBase,
    ShiftTaskCreate,
    ShiftTaskResponse,
    ShiftTaskUpdate,
)
from app.api.schemas.tasks.shift_tasks_bulk import (
    ShiftTaskBulkCreateItem,
    ShiftTaskBulkUpdateItem,
    ShiftTaskBulkUpsertRequest,
    ShiftTaskBulkUpsertResponse,
    ShiftTaskUpsertItem,
)
from app.enums import ShiftTaskStatusEnum, TripStatusRouteEnum, TypesRouteTaskEnum

__all__ = [
    "RouteTaskBase",
    "RouteTaskCreate",
    "RouteTaskUpdate",
    "RouteTaskResponse",
    "RouteTaskBulkCreateItem",
    "RouteTaskBulkUpdateItem",
    "RouteTaskBulkUpsertItem",
    "RouteTaskBulkUpsertRequest",
    "RouteTaskBulkUpsertResponse",
    "ShiftTaskBase",
    "ShiftTaskCreate",
    "ShiftTaskUpdate",
    "ShiftTaskResponse",
    "ShiftTaskBulkCreateItem",
    "ShiftTaskBulkUpdateItem",
    "ShiftTaskUpsertItem",
    "ShiftTaskBulkUpsertRequest",
    "ShiftTaskBulkUpsertResponse",
    "ShiftTaskStatusEnum",
    "TripStatusRouteEnum",
    "TypesRouteTaskEnum",
]
