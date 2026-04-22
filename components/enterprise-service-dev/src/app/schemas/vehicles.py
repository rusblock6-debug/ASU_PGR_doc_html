"""Pydantic schemas для Vehicles."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.enums.vehicles import VehicleStatusEnum, VehicleTypeEnum
from app.schemas.common import PaginationBase
from app.schemas.vehicle_models import VehicleModelResponse


class VehicleBase(BaseModel):
    """Базовая схема транспортного средства."""

    enterprise_id: int = Field(..., description="ID предприятия")
    vehicle_type: VehicleTypeEnum = Field(..., description="Тип техники (shas, pdm, vehicle)")
    name: str = Field(..., min_length=1, max_length=100, description="Название техники")
    model_id: int | None = Field(default=None, description="ID модели")
    serial_number: str | None = Field(default=None, max_length=100, description="Серийный номер")
    registration_number: str | None = Field(
        default=None,
        max_length=50,
        description="Регистрационный номер",
    )
    status: VehicleStatusEnum = Field(
        default=VehicleStatusEnum.active,
        description="Статус техники",
    )
    is_active: bool = Field(default=True, description="Техника активна")
    active_from: date | None = Field(default=None, description="Дата начала активности")
    active_to: date | None = Field(default=None, description="Дата окончания активности")


class VehicleCreate(VehicleBase):
    """Схема создания транспортного средства."""


class VehicleUpdate(BaseModel):
    """Схема обновления транспортного средства.

    Все поля optional - передавайте только те, которые нужно изменить.
    """

    enterprise_id: int | None = Field(default=None, description="ID предприятия")
    vehicle_type: VehicleTypeEnum | None = Field(
        default=None,
        description="Тип техники (shas, pdm, vehicle)",
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Название техники",
    )
    model_id: int | None = Field(default=None, description="ID модели")
    serial_number: str | None = Field(default=None, max_length=100, description="Серийный номер")
    registration_number: str | None = Field(
        default=None,
        max_length=50,
        description="Регистрационный номер",
    )
    status: VehicleStatusEnum | None = Field(default=None, description="Статус техники")
    is_active: bool | None = Field(default=None, description="Техника активна")
    active_from: date | None = Field(default=None, description="Дата начала активности")
    active_to: date | None = Field(default=None, description="Дата окончания активности")


class VehicleResponse(VehicleBase):
    """Ответ транспортного средства."""

    id: int = Field(..., description="ID техники")
    model: VehicleModelResponse | None = Field(default=None, description="Модель техники")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")


class VehicleListResponse(PaginationBase[VehicleResponse]):
    """Ответ списка транспортных средств с пагинацией."""
