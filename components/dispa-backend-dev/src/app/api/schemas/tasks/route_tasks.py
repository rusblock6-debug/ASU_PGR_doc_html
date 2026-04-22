"""Pydantic схемы для route_tasks."""

from typing import Any, Self

from pydantic import ConfigDict, Field, field_serializer, field_validator, model_validator

from app.api.schemas.base import APIBaseModel
from app.api.schemas.common import TimestampBase
from app.enums import TripStatusRouteEnum, TypesRouteTaskEnum


class RouteTaskBase(APIBaseModel):
    """Базовая схема route_task."""

    shift_task_id: str | None = Field(None, description="ID смены")
    route_order: int = Field(..., description="Порядок выполнения внутри смены")
    place_a_id: int = Field(..., description="ID места погрузки")
    place_b_id: int = Field(..., description="ID места разгрузки")
    type_task: TypesRouteTaskEnum = Field(..., description="Тип задания")
    planned_trips_count: int = Field(..., description="Планируемое количество рейсов")
    actual_trips_count: int = Field(..., description="Фактическое количество рейсов")
    status: TripStatusRouteEnum = Field(..., description="Статус задания")
    # TODO route_data устарело, все вынесено в отдельные поля
    route_data: dict[str, Any] | None = Field(
        None,
        description="Дополнительные данные маршрута (payload, сообщение водителю и т. д.)",
    )
    volume: float | None = Field(None, ge=0, description="Объем груза")
    weight: float | None = Field(None, ge=0, description="Вес груза")
    message: str | None = Field(
        None,
        max_length=500,
        description="Сообщение/комментарий к маршруту",
    )

    @field_validator("status", "type_task", mode="before")
    @classmethod
    def status_validator(cls, v: Any) -> Any:
        """Приведение получаемого значение к верхнему регистру."""
        return v.upper() if isinstance(v, str) else v


class RouteTaskCreate(APIBaseModel):
    """Схема создания route_task (поддерживает минимальный payload)."""

    id: str | None = Field(None, description="ID маршрутного задания (опционально)")
    shift_task_id: str | None = Field(
        None,
        description="ID смены; если не передан, используется vehicle_id + текущая смена",
    )
    vehicle_id: int | None = Field(
        None,
        description="ID техники (нужен, если shift_task_id не передан)",
    )
    route_order: int | None = Field(
        None,
        description="Порядок выполнения внутри смены; если не передан — рассчитывается автоматически",
    )
    place_a_id: int = Field(..., description="ID места погрузки")
    place_b_id: int = Field(..., description="ID места разгрузки")
    type_task: TypesRouteTaskEnum = Field(..., description="Тип задания")
    planned_trips_count: int = Field(..., description="Планируемое количество рейсов")
    actual_trips_count: int = Field(0, description="Фактическое количество рейсов")
    status: TripStatusRouteEnum = Field(
        TripStatusRouteEnum.SENT,
        description="Статус задания (по умолчанию SENT)",
    )
    route_data: dict[str, Any] | None = Field(
        None,
        description="Дополнительные данные маршрута (payload, сообщение водителю и т. д.)",
    )
    volume: float = Field(..., ge=0, description="Объем груза")
    weight: float = Field(..., ge=0, description="Вес груза")
    message: str | None = Field(
        None,
        max_length=500,
        description="Сообщение/комментарий к маршруту",
    )

    # Для Swagger/OpenAPI: требуем хотя бы одно из полей
    # shift_task_id или vehicle_id.
    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {"required": ["shift_task_id"]},
                {"required": ["vehicle_id"]},
            ],
        },
    )

    @field_validator("status", "type_task", mode="before")
    @classmethod
    def status_validator(cls, v: Any) -> Any:
        """Приведение получаемого значение к верхнему регистру."""
        return v.upper() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_shift_or_vehicle(self) -> Self:
        """Требуем хотя бы одно поле: shift_task_id или vehicle_id."""
        if self.shift_task_id is None and self.vehicle_id is None:
            raise ValueError("Either shift_task_id or vehicle_id must be provided")
        return self


class RouteTaskUpdate(RouteTaskBase):
    """Схема обновления route_task."""

    route_order: int | None = Field(None, description="Порядок выполнения")  # type: ignore[assignment]
    place_a_id: int | None = Field(None, description="ID места погрузки (place.id)")  # type: ignore[assignment]
    place_b_id: int | None = Field(None, description="ID места разгрузки (place.id)")  # type: ignore[assignment]
    planned_trips_count: int | None = Field(  # type: ignore[assignment]
        None,
        description="Планируемое количество рейсов",
    )
    actual_trips_count: int | None = Field(  # type: ignore[assignment]
        None,
        description="Фактическое количество рейсов",
    )
    type_task: TypesRouteTaskEnum | None = Field(None, description="Тип задания")  # type: ignore[assignment]
    status: TripStatusRouteEnum | None = Field(None, description="Статус задания")  # type: ignore[assignment]


class RouteTaskResponse(RouteTaskBase, TimestampBase):
    """Схема ответа route_task."""

    id: str = Field(..., description="ID маршрутного задания")

    @field_serializer("status")
    def serialize_status(self, value: TripStatusRouteEnum) -> str:
        """Отдавать статус в lower case для фронта."""
        return value.value.lower()

    @field_serializer("type_task")
    def serialize_type_task(self, value: TypesRouteTaskEnum) -> str:
        """Отдавать тип задания в lower case для фронта."""
        return value.value.lower()
