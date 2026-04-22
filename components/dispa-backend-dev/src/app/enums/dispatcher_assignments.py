"""Enums для назначений диспетчера (dispatcher_assignments)."""

from enum import StrEnum


class DispatcherAssignmentKindEnum(StrEnum):
    """Тип источника/цели назначения."""

    ROUTE = "ROUTE"
    NO_TASK = "NO_TASK"
    GARAGE = "GARAGE"


class DispatcherAssignmentStatusEnum(StrEnum):
    """Статус назначения диспетчера."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
