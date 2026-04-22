"""Pydantic schemas для моделей транспорта."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import PaginationBase


class VehicleModelBase(BaseModel):
    """Общие поля для всех схем."""

    max_speed: int | None = Field(default=None, gt=0, description="Мощность двигателя км.ч.")
    tank_volume: float | None = Field(default=None, gt=0, description="Объём бака л.")
    load_capacity_tons: float | None = Field(
        default=None,
        gt=0,
        description="Грузоподъёмность т.",
    )
    volume_m3: float | None = Field(default=None, gt=0, description="Объём кузова/ковша м³")


class VehicleModelCreate(VehicleModelBase):
    """Создание - name обязательно."""

    name: str = Field(..., max_length=100, min_length=1, description="Имя модели")


class VehicleModelUpdate(VehicleModelBase):
    """Обновление - все поля optional."""

    name: str | None = Field(
        default=None,
        max_length=100,
        min_length=1,
        description="Имя модели",
    )


class VehicleModelResponse(VehicleModelBase):
    """Ответ модели транспорта."""

    id: int = Field(..., description="ID модели транспорта")
    name: str = Field(..., max_length=100, min_length=1, description="Имя модели")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")

    model_config = {"from_attributes": True}


class VehicleModelListResponse(PaginationBase[VehicleModelResponse]):
    """Ответ списка моделей транспорта с пагинацией."""
