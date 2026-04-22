"""Enums перечисление допустимых значений для валидации и документации Swagger."""

from .dispatcher_assignments import (
    DispatcherAssignmentKindEnum,
    DispatcherAssignmentStatusEnum,
)
from .place_remaining_history import RemainingChangeTypeEnum
from .route_tasks import TripStatusRouteEnum, TypesRouteTaskEnum
from .shift_tasks import ShiftTaskStatusEnum

__all__ = [
    # Dispatcher assignments
    "DispatcherAssignmentKindEnum",
    "DispatcherAssignmentStatusEnum",
    # Place_remaining_history
    "RemainingChangeTypeEnum",
    # Route_task
    "TripStatusRouteEnum",
    "TypesRouteTaskEnum",
    # Shift_task
    "ShiftTaskStatusEnum",
]
