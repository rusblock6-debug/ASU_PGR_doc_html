"""Pydantic схемы для shift_tasks."""

from datetime import datetime
from typing import Any

from pydantic import Field, field_serializer, field_validator

from app.api.schemas.base import APIBaseModel
from app.api.schemas.common import TimestampBase
from app.api.schemas.tasks.route_tasks import RouteTaskResponse
from app.api.schemas.tasks.route_tasks_bulk import RouteTaskBulkCreateItem, RouteTaskBulkUpsertItem
from app.enums import ShiftTaskStatusEnum


class ShiftTaskBase(APIBaseModel):
    """Схема создания shift_task с route_tasks."""

    work_regime_id: int = Field(..., description="ID режима работы")
    vehicle_id: int = Field(..., description="ID транспортного средства")
    shift_date: str = Field(..., description="Дата смены (YYYY-MM-DD)")
    shift_num: int = Field(..., description="Номер смены", ge=1)
    task_name: str | None = Field(None, description="Название задания")
    priority: int = Field(0, description="Приоритет")
    status: ShiftTaskStatusEnum = Field(..., description="Статус")
    sent_to_board_at: datetime | None = Field(None, description="Когда отправлено на борт")
    acknowledged_at: datetime | None = Field(None, description="Когда подтверждено")
    started_at: datetime | None = Field(None, description="Когда начато")
    completed_at: datetime | None = Field(None, description="Когда завершено")
    task_data: dict[str, Any] | None = Field(None, description="Дополнительные данные")

    route_tasks: list[RouteTaskBulkCreateItem] = Field(default_factory=list, description="Маршрутные задания")

    @field_validator("status", mode="before")
    @classmethod
    def status_validator(cls, v: Any) -> Any:
        """Приведение получаемого значение к верхнему регистру."""
        return v.upper() if isinstance(v, str) else v


class ShiftTaskCreate(ShiftTaskBase):
    """Схема создания shift_task с route_tasks."""

    status: ShiftTaskStatusEnum = Field(ShiftTaskStatusEnum.PENDING, description="Статус")


class ShiftTaskUpdate(ShiftTaskBase):
    """Схема обновления shift_task с route_tasks."""

    work_regime_id: int | None = Field(None, description="ID режима работы")  # type: ignore[assignment]
    vehicle_id: int | None = Field(None, description="ID транспортного средства")  # type: ignore[assignment]
    shift_date: str | None = Field(None, description="Дата смены")  # type: ignore[assignment]
    shift_num: int | None = Field(None, description="Номер смены", ge=1)  # type: ignore[assignment]
    priority: int | None = Field(None, description="Приоритет")  # type: ignore[assignment]
    status: ShiftTaskStatusEnum | None = Field(None, description="Статус")  # type: ignore[assignment]

    route_tasks: list[RouteTaskBulkUpsertItem] | None = Field(None, description="Маршрутные задания")  # type: ignore[assignment]


class ShiftTaskResponse(ShiftTaskBase, TimestampBase):
    """Схема ответа shift_task с route_tasks."""

    id: str = Field(..., description="ID нарядного задания")
    priority: int = Field(..., description="Приоритет")

    route_tasks: list[RouteTaskResponse] = Field(default_factory=list, description="Маршрутные задания")  # type: ignore[assignment]

    @field_serializer("status")
    def serialize_status(self, value: ShiftTaskStatusEnum) -> str:
        """Отдавать статус в lower case для фронта."""
        return value.value.lower()
