"""Pydantic схемы для trips."""

import re
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.schemas.base import APIBaseModel


class TripValidationMixin:
    """Миксин с общей логикой валидации временных полей для рейсов."""

    @model_validator(mode="after")
    def validate_loading_timestamp_not_before_trip_start(self) -> Self:
        """Время начала погрузки не может быть меньше времени начала рейса.

        Для TripCreate: loading_timestamp >= cycle_started_at
        Для TripUpdate: loading_timestamp >= start_time (или cycle_started_at если start_time не указан)
        """
        # Получаем время начала рейса в зависимости от типа модели
        trip_start_time = getattr(self, "start_time", None) or getattr(self, "cycle_started_at", None)
        loading_timestamp = getattr(self, "loading_timestamp", None)

        if loading_timestamp is not None and trip_start_time is not None and loading_timestamp < trip_start_time:
            raise ValueError("Время начала погрузки не может быть меньше времени начала рейса")

        return self


class TripCreate(TripValidationMixin, BaseModel):
    """Схема создания рейса."""

    vehicle_id: int = Field(..., description="ID транспорта")
    cycle_started_at: datetime = Field(..., description="Время начала цикла")
    loading_place_id: int | None = Field(None, description="ID места погрузки (place.id)")
    loading_timestamp: datetime | None = Field(None, description="Время погрузки")
    unloading_place_id: int | None = Field(None, description="ID места разгрузки (place.id)")
    unloading_timestamp: datetime | None = Field(None, description="Время разгрузки")
    cycle_completed_at: datetime | None = Field(None, description="Время завершения цикла")
    change_amount: float | None = Field(
        None,
        description=("Фактический объем/вес рейса для пересчета остатков."),
    )


class TripUpdate(TripValidationMixin, BaseModel):
    """Схема обновления рейса."""

    vehicle_id: int = Field(..., description="ID транспорта")
    loading_place_id: int = Field(..., description="ID места погрузки (place.id)")
    loading_timestamp: datetime = Field(..., description="Время погрузки")
    unloading_place_id: int = Field(..., description="ID места разгрузки (place.id)")
    unloading_timestamp: datetime = Field(..., description="Время разгрузки")
    cycle_started_at: datetime = Field(..., description="Время начала цикла")
    cycle_completed_at: datetime = Field(..., description="Время завершения цикла")
    change_amount: float | None = Field(
        None,
        description=(
            "Фактический объем/вес рейса для пересчета остатков. "
            "Если указан, для завершенного рейса будут пересчитаны записи "
            "PlaceRemainingHistory (loading/unloading) и запущен пересчет остатков."
        ),
    )


class TripResponse(APIBaseModel):
    """Схема ответа trip (наследуется от Cycle через JTI)."""

    # Основные поля (наследуются от Cycle через JTI)
    cycle_id: str = Field(..., description="ID цикла/рейса (первичный ключ, одинаковый для Cycle и Trip)")
    cycle_num: int | None = Field(None, description="Порядковый номер рейса в рамках смены")
    vehicle_id: int = Field(..., description="ID транспорта")
    task_id: str | None = Field(None, description="ID задания")
    shift_id: str | None = Field(None, description="ID смены")
    change_amount: float | None = Field(None, description="change_amount цикла")

    # Названия мест (только для GET запросов, не в модели)
    loading_place_name: str | None = Field(None, description="Название места погрузки")
    unloading_place_name: str | None = Field(None, description="Название места разгрузки")

    # Поля цикла
    from_place_id: int | None = Field(None, description="Место начала цикла (place.id)")
    to_place_id: int | None = Field(None, description="Место окончания цикла (place.id)")
    cycle_started_at: datetime | None = Field(
        None,
        description="Время начала цикла (начало движения порожним)",
    )
    cycle_completed_at: datetime | None = Field(
        None,
        description="Время завершения цикла (окончание разгрузки)",
    )
    source: Literal["dispatcher", "system"] = Field(
        "system",
        description="Источник создания цикла (dispatcher/system)",
    )

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Валидация значения source."""
        if v is None:
            return "system"  # Значение по умолчанию
        if v not in ("dispatcher", "system"):
            raise ValueError("source должен быть 'dispatcher' или 'system'")
        return v

    # Поля рейса
    trip_type: str | None = Field(None, description="Тип рейса (planned/unplanned)")
    start_time: datetime | None = Field(None, description="Время начала рейса")
    end_time: datetime | None = Field(None, description="Время окончания рейса")
    loading_place_id: int | None = Field(None, description="ID места погрузки (place.id)")
    unloading_place_id: int | None = Field(None, description="ID места разгрузки (place.id)")
    loading_tag: str | None = Field(None, description="Tag погрузки")
    unloading_tag: str | None = Field(None, description="Tag разгрузки")
    loading_timestamp: datetime | None = Field(None, description="Время погрузки")
    unloading_timestamp: datetime | None = Field(None, description="Время разгрузки")

    # Метки времени
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")


class CycleStateHistoryResponse(APIBaseModel):
    """Схема ответа cycle_state_history."""

    id: int = Field(..., description="ID записи")
    timestamp: datetime = Field(..., description="Временная метка")
    vehicle_id: int = Field(..., description="ID транспорта")
    cycle_id: str | None = Field(None, description="ID цикла (может быть Cycle или Trip)")
    state: str = Field(..., description="Состояние State Machine")
    state_data: dict[str, Any] = Field(..., description="Данные состояния")
    place_id: int | None = Field(None, description="ID места")
    source: str = Field(..., description="Источник изменения: dispatcher или system")
    task_id: str | None = Field(None, description="ID задачи (UUID4)")
    trigger_type: str = Field(..., description="Тип триггера")
    trigger_data: dict[str, Any] | None = Field(None, description="Данные триггера")


class CycleTagHistoryResponse(APIBaseModel):
    """Схема ответа cycle_tag_history."""

    id: int = Field(..., description="ID записи")
    timestamp: datetime = Field(..., description="Временная метка")
    vehicle_id: int = Field(..., description="ID транспорта")
    cycle_id: str | None = Field(None, description="ID цикла (может быть Cycle или Trip)")
    point_id: str = Field(..., description="ID тега (tag.point_id)")
    place_id: int | None = Field(None, description="ID места (place.id)")
    tag: str = Field(..., description="Тег локации")
    extra_data: dict[str, Any] | None = Field(None, description="Дополнительные данные")

    @field_validator("point_id")
    @classmethod
    def validate_point_id_format(cls, v: str) -> str:
        """Валидация формата point_id."""
        if not v or not v.strip():
            raise ValueError("point_id не может быть пустым")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("point_id может содержать только буквы, цифры, дефис и подчеркивание")
        return v.strip()


class CycleAnalyticsResponse(APIBaseModel):
    """Схема ответа cycle_analytics - полная аналитика цикла/рейса."""

    id: int = Field(..., description="ID записи")
    cycle_id: str | None = Field(None, description="ID рейса")
    vehicle_id: int = Field(..., description="ID транспорта")
    shift_id: str | None = Field(None, description="ID смены")
    trip_type: str | None = Field(None, description="Тип рейса")
    trip_status: str | None = Field(None, description="Статус рейса")
    from_place_id: int | None = Field(None, description="Место отправления (place.id)")
    to_place_id: int | None = Field(None, description="Место назначения (place.id)")
    trip_started_at: datetime | None = Field(None, description="Время начала рейса")
    trip_completed_at: datetime | None = Field(None, description="Время завершения рейса")
    total_duration_seconds: float | None = Field(None, description="Общая длительность")
    moving_empty_duration_seconds: float | None = Field(None, description="Движение порожним")
    stopped_empty_duration_seconds: float | None = Field(None, description="Остановка порожним")
    loading_duration_seconds: float | None = Field(None, description="Длительность погрузки")
    moving_loaded_duration_seconds: float | None = Field(None, description="Движение с грузом")
    stopped_loaded_duration_seconds: float | None = Field(None, description="Остановка с грузом")
    unloading_duration_seconds: float | None = Field(None, description="Длительность разгрузки")
    state_transitions_count: int | None = Field(None, description="Количество переходов состояний")
    analytics_data: dict[str, Any] | None = Field(None, description="Дополнительная аналитика")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")


# Алиасы для совместимости с server mode API
TripAnalyticsResponse = CycleAnalyticsResponse
