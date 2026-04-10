"""Pydantic схемы для shift_tasks bulk."""

from pydantic import Field

from app.api.schemas.base import APIBaseModel
from app.api.schemas.common import BulkResponse
from app.api.schemas.tasks.route_tasks_bulk import RouteTaskBulkUpsertItem
from app.api.schemas.tasks.shift_tasks import (
    ShiftTaskBase,
    ShiftTaskCreate,
    ShiftTaskUpdate,
)
from app.enums import ShiftTaskStatusEnum


class ShiftTaskBulkCreateItem(ShiftTaskCreate):
    """Элемент для bulk create shift_task."""


class ShiftTaskBulkUpdateItem(ShiftTaskUpdate):
    """Элемент для bulk update shift_task."""

    id: str = Field(..., description="ID нарядного задания")


class ShiftTaskUpsertItem(ShiftTaskBase):
    """Элемент для bulk upsert shift_task.

    Логика:
    - id указан → UPDATE shift_task (+ route_tasks UPDATE)
        - если route_tasks = [] - DELETE все route_tasks которые есть но не указанны
        - если route_tasks = None - ничего не меняем
    - id НЕ указан → CREATE shift_task (+ route_tasks только CREATE)
    """

    # ID опциональный
    id: str | None = Field(None, description="ID shift task (None = create)")

    # Основные поля (обязательные для CREATE, опциональные для UPDATE)
    work_regime_id: int | None = Field(None, description="ID режима работы")  # type: ignore[assignment]
    vehicle_id: int | None = Field(None, description="ID транспортного средства")  # type: ignore[assignment]
    shift_date: str | None = Field(None, description="Дата смены (YYYY-MM-DD)")  # type: ignore[assignment]
    shift_num: int | None = Field(None, description="Номер смены", ge=1)  # type: ignore[assignment]
    priority: int | None = Field(None, description="Приоритет")  # type: ignore[assignment]
    status: ShiftTaskStatusEnum | None = Field(None, description="Статус")  # type: ignore[assignment]

    # Вложенные route_tasks (используем RouteTaskNestedItem!)
    route_tasks: list[RouteTaskBulkUpsertItem] | None = Field(  # type: ignore[assignment]
        None,
        description="Вложенные route_tasks (None = не трогать, [] = удалить все)",
    )


class ShiftTaskBulkUpsertRequest(APIBaseModel):
    """Запрос для bulk upsert shift_tasks."""

    items: list[ShiftTaskUpsertItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Элементы для upsert (1-100)",
    )


class ShiftTaskBulkUpsertResponse(BulkResponse):
    """Ответ после bulk upsert."""
