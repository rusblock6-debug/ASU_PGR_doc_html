"""Pydantic схемы для rout tasks bulk."""

from typing import Any

from pydantic import BaseModel, Field

from app.api.schemas.common import BulkResponse
from app.api.schemas.tasks.route_tasks import (
    RouteTaskBase,
    RouteTaskCreate,
    RouteTaskUpdate,
)
from app.enums import TripStatusRouteEnum, TypesRouteTaskEnum


class RouteTaskBulkCreateItem(RouteTaskCreate):
    """Элемент для bulk create route_tasks."""

    shift_task_id: str | None = Field(None, description="ID смены")


class RouteTaskBulkUpdateItem(RouteTaskUpdate):
    """Элемент для bulk update route_tasks."""

    id: str = Field(..., description="ID маршрутного задания")


class RouteTaskBulkUpsertItem(RouteTaskBase):
    """Элемент для bulk upsert (создание или обновление).

    Логика:
    - id = None → CREATE (генерируется новый ID)
    - id указан → UPDATE (обновляется существующая запись)
    """

    id: str | None = Field(None, description="ID route task (None = create)")

    route_order: int | None = Field(..., description="Порядок выполнения внутри смены")  # type: ignore[assignment]
    place_a_id: int | None = Field(..., description="ID места погрузки")  # type: ignore[assignment]
    place_b_id: int | None = Field(..., description="ID места разгрузки")  # type: ignore[assignment]
    planned_trips_count: int | None = Field(1, description="Планируемое количество", ge=0)  # type: ignore[assignment]
    actual_trips_count: int | None = Field(0, description="Фактическое количество", ge=0)  # type: ignore[assignment]
    status: TripStatusRouteEnum | None = Field(  # type: ignore[assignment]
        TripStatusRouteEnum.EMPTY,
        description="Статус",
    )
    type_task: TypesRouteTaskEnum | None = Field(  # type: ignore[assignment]
        None,
        description="Тип задания",
    )

    route_data: dict[str, Any] | None = Field(
        None,
        description="Дополнительные данные JSONB",
    )


class RouteTaskBulkUpsertRequest(BaseModel):
    """Запрос для bulk upsert (создание + обновление)."""

    items: list[RouteTaskBulkUpsertItem] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Элементы для upsert (1-500)",
    )


class RouteTaskBulkUpsertResponse(BulkResponse):
    """Ответ после bulk upsert."""
