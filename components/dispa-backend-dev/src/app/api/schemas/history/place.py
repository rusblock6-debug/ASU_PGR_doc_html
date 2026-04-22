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
    # тогда change_volume будет вычислен сервером.
    change_volume: float | None = None
    # Тип груза (load_type.id) и вес груза (тонны) — опционально, для сохранения ВГ в истории.
    load_type_id: int | None = None
    change_weight: float | None = None
    # Для ручных правок остатка в place (из graph-service/UI) удобнее передавать целевое значение.
    # Если задано, сервер посчитает корректирующую дельту и сохранит ее в change_volume.
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
