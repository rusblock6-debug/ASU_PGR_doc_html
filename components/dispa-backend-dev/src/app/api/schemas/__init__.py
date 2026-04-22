"""Pydantic schemas для API валидации."""

from .common import (
    BulkResponse,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    TimestampBase,
)
from .event_log import (
    CycleStateHistoryBatchItem,
    CycleStateHistoryBatchRequest,
    CycleStateHistoryBatchResponse,
    CycleStateHistoryBatchResultItem,
)
from .history import PlaceRemainingHistoryCreate
from .state import (
    ManualTransitionRequest,
    StateMachineResponse,
)
from .tasks import (
    RouteTaskBase,
    RouteTaskBulkCreateItem,
    RouteTaskBulkUpdateItem,
    RouteTaskBulkUpsertItem,
    RouteTaskBulkUpsertRequest,
    RouteTaskBulkUpsertResponse,
    RouteTaskCreate,
    RouteTaskResponse,
    RouteTaskUpdate,
    ShiftTaskBase,
    ShiftTaskBulkCreateItem,
    ShiftTaskBulkUpdateItem,
    ShiftTaskBulkUpsertRequest,
    ShiftTaskBulkUpsertResponse,
    ShiftTaskCreate,
    ShiftTaskResponse,
    ShiftTaskStatusEnum,
    ShiftTaskUpdate,
    ShiftTaskUpsertItem,
    TripStatusRouteEnum,
    TypesRouteTaskEnum,
)
from .trips import (
    TripCreate,
    TripResponse,
    TripUpdate,
)

__all__ = [
    # Common schemas
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    "BulkResponse",
    "TimestampBase",
    # Route_task schemas
    "RouteTaskBase",
    "RouteTaskCreate",
    "RouteTaskUpdate",
    "RouteTaskResponse",
    # Route_task bulk schemas
    "RouteTaskBulkCreateItem",
    "RouteTaskBulkUpdateItem",
    "RouteTaskBulkUpsertItem",
    "RouteTaskBulkUpsertRequest",
    "RouteTaskBulkUpsertResponse",
    # Shift_task schemas
    "ShiftTaskBase",
    "ShiftTaskCreate",
    "ShiftTaskUpdate",
    "ShiftTaskResponse",
    # Shift_task bulk schemas
    "ShiftTaskBulkCreateItem",
    "ShiftTaskBulkUpdateItem",
    "ShiftTaskUpsertItem",
    "ShiftTaskBulkUpsertRequest",
    "ShiftTaskBulkUpsertResponse",
    # Event log schemas
    "CycleStateHistoryBatchItem",
    "CycleStateHistoryBatchRequest",
    "CycleStateHistoryBatchResultItem",
    "CycleStateHistoryBatchResponse",
    # State machine schemas
    "StateMachineResponse",
    "ManualTransitionRequest",
    # Trip schemas
    "TripCreate",
    "TripUpdate",
    "TripResponse",
    # Enums
    "TripStatusRouteEnum",
    "TypesRouteTaskEnum",
    "ShiftTaskStatusEnum",
    # History schemas
    "PlaceRemainingHistoryCreate",
]
