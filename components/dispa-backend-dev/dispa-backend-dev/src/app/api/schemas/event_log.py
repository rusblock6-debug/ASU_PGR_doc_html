"""Pydantic схемы для журнала событий (Event Log)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.api.schemas.base import APIBaseModel

# ============================================================================
# Схемы для batch операций с cycle_state_history
# ============================================================================


class CycleStateHistoryBatchItem(BaseModel):
    """Элемент для batch создания/редактирования cycle_state_history.

    При наличии id - редактирование существующей записи.
    При отсутствии id - создание новой записи с валидацией StateMachine.
    """

    id: str | None = Field(None, description="ID записи (если указан - редактирование)")
    timestamp: datetime | None = Field(
        None,
        description="Время события (если не указано - используется текущее время)",
    )
    system_name: str = Field(
        ...,
        description="Системное имя состояния (idle, moving_empty, stopped_empty, "
        "loading, moving_loaded, stopped_loaded, unloading)",
    )
    system_status: bool = Field(
        True,
        description="Системный статус. True - валидация переходов StateMachine, False - любой переход разрешен",
    )
    is_end_of_cycle: bool | None = Field(
        None,
        description="Признак окончания цикла. Если true, то этот статус завершает цикл",
    )
    cycle_id: str | None = Field(
        None,
        description="ID цикла (если указан при создании - используется этот cycle_id без поиска активного цикла)",
    )


class CycleStateHistoryBatchRequest(BaseModel):
    """Запрос на batch создание/редактирование cycle_state_history."""

    vehicle_id: int = Field(..., description="ID транспортного средства")
    items: list[CycleStateHistoryBatchItem] = Field(
        ...,
        min_length=1,
        description="Массив элементов для создания/редактирования",
    )


class CycleStateHistoryBatchResultItem(BaseModel):
    """Результат операции над одним элементом."""

    id: str = Field(..., description="ID записи")
    operation: str = Field(..., description="Тип операции: created, updated")
    state: str = Field(..., description="Состояние")
    timestamp: datetime = Field(..., description="Время события")
    cycle_id: str | None = Field(None, description="ID цикла")
    cycle_action: str | None = Field(None, description="Действие с циклом: created, completed, none")


class CycleStateHistoryBatchResponse(BaseModel):
    """Ответ на batch запрос."""

    success: bool = Field(..., description="Успех операции")
    message: str = Field(..., description="Сообщение")
    results: list[CycleStateHistoryBatchResultItem] = Field(
        default_factory=list,
        description="Результаты для каждого элемента",
    )
    cycles_created: int = Field(0, description="Количество созданных циклов")
    cycles_completed: int = Field(0, description="Количество завершенных циклов")


# ============================================================================
# Схемы для удаления cycle_state_history
# ============================================================================


class StateHistoryDeleteRequest(BaseModel):
    """Запрос на удаление записи cycle_state_history."""

    confirm: bool = Field(
        False,
        description="Подтверждение удаления (требуется если удаление приведет к удалению цикла)",
    )


class StateHistoryDeleteResponse(BaseModel):
    """Ответ на запрос удаления."""

    success: bool = Field(..., description="Успех операции")
    message: str = Field(..., description="Сообщение для подтверждения удаления")
    forbidden: bool = Field(default=False, description="Операция запрещена (HTTP 400)")
    cycle_id: str | None = Field(default=None, description="ID цикла который будет удален")
    deleted_record_id: str | None = Field(default=None, description="ID удаленной записи")
    cycle_deleted: bool = Field(default=False, description="Был ли удален цикл")
    trip_deleted: bool = Field(default=False, description="Был ли удален рейс")
    fields_cleared: list[str] = Field(
        default_factory=list,
        description="Список очищенных полей в цикле/рейсе",
    )


# ============================================================================
# Схемы ответов для истории
# ============================================================================


class CycleStateHistoryResponse(APIBaseModel):
    """Ответ для истории состояний State Machine."""

    type_name: Literal["cycle_state_history"] = Field(
        ...,
        description="Идентификатор типа записи для фронта",
    )
    id: str = Field(..., description="UUID записи истории")
    timestamp: datetime = Field(..., description="Время события")
    vehicle_id: int = Field(..., description="ID машины")
    cycle_id: str | None = Field(None, description="ID рейса")
    state: str = Field(..., description="Состояние State Machine")
    source: str = Field(..., description="Источник изменения: dispatcher или system")
    task_id: str | None = Field(None, description="ID задачи (UUID4)")
    place_id: int | None = Field(None, description="ID места")

    @model_validator(mode="before")
    @classmethod
    def _ensure_type_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and "type_name" not in data:
            return {**data, "type_name": "cycle_state_history"}
        if hasattr(data, "__table__"):
            d = {c.key: getattr(data, c.key) for c in data.__table__.columns}
            d["type_name"] = "cycle_state_history"
            return d
        return data


class CycleTagHistoryResponse(APIBaseModel):
    """Ответ для истории меток локации."""

    id: str = Field(..., description="UUID записи истории")
    timestamp: datetime = Field(..., description="Время события")
    vehicle_id: int = Field(..., description="ID машины")
    cycle_id: str | None = Field(None, description="ID рейса")
    point_id: str = Field(..., description="ID точки")
    place_id: int | None = Field(None, description="ID места")
    extra_data: dict[str, Any] | None = Field(None, description="Дополнительные данные")


class FullShiftStateHistoryResponse(APIBaseModel):
    """Ответ для обобщенной истории состояний смен."""

    type_name: Literal["full_shift_state_history"] = Field(
        ...,
        description="Идентификатор типа записи для фронта",
    )
    id: str = Field(..., description="UUID записи")
    timestamp: datetime = Field(..., description="Время начала смены")
    vehicle_id: int = Field(..., description="ID машины")
    shift_num: int = Field(..., description="Номер смены")
    shift_date: str = Field(..., description="Дата смены")
    state: str = Field(..., description="Обобщенное состояние: work, idle, no_data")
    source: str = Field(..., description="Источник данных")
    idle_duration: int | None = Field(
        ...,
        description="Длительность простоя в секундах (null если нет данных)",
    )
    work_duration: int | None = Field(
        ...,
        description="Длительность работы в секундах (null если нет данных)",
    )

    @model_validator(mode="before")
    @classmethod
    def _ensure_type_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and "type_name" not in data:
            return {**data, "type_name": "full_shift_state_history"}
        if hasattr(data, "__table__"):
            d = {c.key: getattr(data, c.key) for c in data.__table__.columns}
            d["type_name"] = "full_shift_state_history"
            return d
        return data


class EventLogListResponse(BaseModel):
    """Ответ со списком событий."""

    items: list[CycleStateHistoryResponse | CycleTagHistoryResponse | FullShiftStateHistoryResponse] = Field(
        ...,
        description="Список событий",
    )
    total: int = Field(..., description="Общее количество событий")
    page: int = Field(..., description="Номер страницы")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Всего страниц")


class CurrentShiftStatsResponse(BaseModel):
    """Сводная статистика по текущей смене."""

    shift_date: str = Field(..., description="Дата текущей смены")
    shift_num: int = Field(..., description="Номер текущей смены")
    work_time_sum: int = Field(
        ...,
        description="Суммарная длительность статусов с is_work_status=true, в минутах",
    )
    idle_time_sum: int = Field(
        ...,
        description="Суммарная длительность статусов с is_work_status=false, в минутах",
    )
    actual_trips_count_sum: int = Field(
        ...,
        description="Суммарное количество завершенных рейсов за смену (trips с end_time)",
    )
    planned_trips_count_sum: int = Field(
        ...,
        description="Суммарное плановое количество рейсов за смену (SUM route_tasks.planned_trips_count)",
    )
    actual_weight_sum: int = Field(
        ...,
        description="Суммарный фактический объем за смену (положительные change_amount из place_remaining_history)",
    )
    planned_weight_sum: int = Field(
        ...,
        description="Суммарный плановый вес за смену (SUM route_tasks.weight)",
    )
