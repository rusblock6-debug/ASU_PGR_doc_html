"""Pydantic схемы для map_settings."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TimestampBase


class MapSettingsResponse(TimestampBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int = Field(..., description="ID записи настроек")
    routes_color: str = Field(
        ...,
        alias="RoutesColor",
        description="HEX цвет маршрутов (#RRGGBB)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )


class MapSettingValueResponse(BaseModel):
    setting_name: str = Field(..., description="Имя настройки")
    value: str = Field(..., description="Текущее значение настройки")


class MapSettingValueUpdate(BaseModel):
    value: str = Field(
        ...,
        description="Новое значение настройки",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )
