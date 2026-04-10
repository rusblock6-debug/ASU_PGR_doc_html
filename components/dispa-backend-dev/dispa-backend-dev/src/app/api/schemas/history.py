"""Pydantic схемы для истории остатков."""

from datetime import datetime

from app.api.schemas.base import APIBaseModel
from app.enums import RemainingChangeTypeEnum


class PlaceRemainingHistoryBase(APIBaseModel):
    """Базовая схема истории остатков."""

    place_id: int
    change_type: RemainingChangeTypeEnum
    # Для рейсов (loading/unloading) это обязательная дельта.
    # Для ручной корректировки (manual) можно передать target_stock,
    # тогда change_amount будет вычислен сервером.
    change_amount: float | None = None
    # Для ручных правок остатка в place (из graph-service/UI) удобнее передавать целевое значение.
    # Если задано, сервер посчитает корректирующую дельту и сохранит ее в change_amount.
    target_stock: float | None = None
    timestamp: datetime
    cycle_id: str | None = None
    task_id: str | None = None
    shift_id: str | None = None
    # Для ручных правок остатка места vehicle_id может быть неизвестен/не применим.
    vehicle_id: int | None = None
    source: str = "system"


class PlaceRemainingHistoryCreate(PlaceRemainingHistoryBase):
    """Схема создания записи истории остатков."""

    pass


class PlaceRemainingHistoryResponse(PlaceRemainingHistoryBase):
    """Схема ответа истории остатков."""

    id: str
