"""Схемы событий истории машины с привязкой телеметрии."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from platform_sdk.analytics import CycleTagHistoryResponse
from pydantic import BaseModel, Field

from app.api.schemas.event_log import CycleStateHistoryResponse


class VehicleTelemetry(BaseModel):
    """Ближайшая точка телеметрии, сопоставленная с событием истории."""

    timestamp: datetime
    lat: float
    lon: float
    height: float | None = None
    speed: float | None = None
    fuel: float | None = None


class HistoryEventType(StrEnum):
    """Тип события в объединённой истории."""

    tag_history = "tag_history"
    state_history = "state_history"
    trip_history = "trip_history"


class StateHistoryItem(BaseModel):
    """Элемент истории состояний State Machine."""

    event_type: Literal[HistoryEventType.state_history] = HistoryEventType.state_history
    data: CycleStateHistoryResponse
    telemetry: VehicleTelemetry | None = None


class TagHistoryItem(BaseModel):
    """Элемент истории меток локации."""

    event_type: Literal[HistoryEventType.tag_history] = HistoryEventType.tag_history
    data: CycleTagHistoryResponse
    telemetry: VehicleTelemetry | None = None


type HistoryItem = Annotated[
    StateHistoryItem | TagHistoryItem,
    Field(discriminator="event_type"),
]
