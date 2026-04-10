"""Pydantic schemas для Enterprise Settings."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EnterpriseSettingsBase(BaseModel):
    """Базовая схема параметров предприятия."""

    enterprise_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Название предприятия",
    )
    timezone: str = Field(default="Europe/Moscow", max_length=50, description="Часовой пояс")
    address: str | None = Field(None, description="Адрес")
    phone: str | None = Field(None, max_length=20, description="Телефон")
    email: str | None = Field(None, max_length=100, description="Email")
    coordinates: dict[str, Any] | None = Field(None, description="Координаты (GeoJSON point)")
    settings_data: dict[str, Any] | None = Field(None, description="Дополнительные данные")


class EnterpriseSettingsCreate(EnterpriseSettingsBase):
    """Схема создания параметров предприятия."""

    pass


class EnterpriseSettingsUpdate(BaseModel):
    """Схема обновления параметров предприятия."""

    enterprise_name: str | None = None
    timezone: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    coordinates: dict[str, Any] | None = None
    settings_data: dict[str, Any] | None = None


class EnterpriseSettingsResponse(EnterpriseSettingsBase):
    """Ответ параметров предприятия."""

    id: int = Field(..., description="ID предприятия")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: datetime = Field(..., description="Время обновления")

    class Config:
        """Конфигурация Pydantic модели."""

        from_attributes = True
