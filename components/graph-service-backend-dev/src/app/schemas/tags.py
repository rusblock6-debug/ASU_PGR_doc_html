"""Pydantic модели для graph-service"""

import re
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.enum.places import PlaceTypeEnum
from app.schemas.base import APIBaseModel


class APITagBaseModel(APIBaseModel):
    """Базовая модель метки"""

    # x: float = Field(..., description="Canvas координаты X (beacon_placement)")
    # y: float = Field(..., description="Canvas координаты Y (beacon_placement)")
    radius: float = Field(
        default=25.0,
        description="Радиус действия в метрах (beacon_radius)",
    )
    # name: str = Field(..., description="Название метки")
    # point_type: PointTypeEnum = Field(..., description="Тип метки (beacon_type)")
    tag_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Обратная совместимость: beacon_id (Идентификатор метки)",
    )
    tag_mac: str = Field(
        ...,
        min_length=1,
        max_length=17,
        description=(
            "MAC адрес метки в формате XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX или XXXXXXXXXXXX"
        ),
    )
    battery_level: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Уровень заряда (beacon_power, только для чтения)",
    )
    battery_updated_at: datetime | None = Field(
        None,
        description="Дата изменения уровня заряда",
    )
    place_id: int | None = Field(None, description="ID места")

    @field_validator("battery_updated_at", mode="before")
    def parse_datetime_fields(cls, value: str | datetime | None) -> datetime | None:
        if value is None:
            return value

        if isinstance(value, datetime):
            return value.replace(tzinfo=None)  # Убеждаемся, что нет временной зоны

        # Обрабатываем строку
        value = value.strip()

        # Убираем Z и парсим как UTC
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(value)
            # Убираем временную зону для consistency
            return dt.replace(tzinfo=None)
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {value}") from e

    @field_validator("tag_mac")
    @classmethod
    def validate_tag_mac_format(cls, v: str | None) -> str | None:
        """Валидация формата MAC адреса"""
        if not v:
            return None
        v = v.strip()
        if not v:
            return None
        # Поддерживаем форматы: XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX или XXXXXXXXXXXX
        mac_pattern = re.compile(
            r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$",
        )
        if not mac_pattern.match(v):
            raise ValueError(
                "MAC адрес должен быть в формате XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX",
            )
        # Нормализуем к формату с двоеточиями
        v_clean = v.replace("-", "").replace(":", "").upper()
        return ":".join([v_clean[i : i + 2] for i in range(0, 12, 2)])


class APIPlaceTagResponseModel(APIBaseModel):
    name: str = Field(description="Место установки")
    type: PlaceTypeEnum = Field(description="Тип метки")
    location: dict | None = Field(
        None,
        description="Местоположение (для обратной совместимости, создается из geometry)",
    )


class APITagCreateModel(APITagBaseModel):
    """Модель для создания метки"""

    tag_id: str | None = Field(
        None,
        description="Алиас для tag_name (для обратной совместимости)",
    )

    @model_validator(mode="after")
    def set_tag_name_from_tag_id(self):
        """Если передан tag_id, но не tag_name, используем tag_id как tag_name"""
        if self.tag_id and (not self.tag_name or self.tag_name is None):
            self.tag_name = self.tag_id
        if not self.tag_name or self.tag_name is None:
            raise ValueError("tag_name или tag_id обязательны для создания метки")
        return self


class APITagUpdateModel(APIBaseModel):
    """Модель для обновления метки"""

    # Основные поля метки (опциональные для обновления)
    tag_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Обратная совместимость: beacon_id (Идентификатор метки)",
    )
    tag_mac: str | None = Field(None, min_length=1, max_length=17, description="MAC адрес метки")
    radius: float | None = Field(None, description="Радиус действия в метрах")
    place_id: int | None = Field(None, description="ID места")
    battery_level: float | None = Field(None, ge=0, le=100, description="Уровень заряда")
    battery_updated_at: datetime | None = Field(None, description="Дата изменения уровня заряда")

    # Поля для обратной совместимости
    beacon_mac: str | None = Field(None, description="Алиас для tag_mac")
    beacon_id: str | None = Field(None, description="Алиас для tag_name")
    point_id: str | None = Field(None, description="Алиас для tag_name")
    name: str | None = Field(None, description="Название места (для обновления через place)")
    point_type: str | None = Field(None, description="Тип места (для обновления через place)")
    beacon_place: str | None = Field(
        None,
        description="Название места (для обновления через place)",
    )
    x: float | None = Field(None, description="Координата X места (GPS lon)")
    y: float | None = Field(None, description="Координата Y места (GPS lat)")

    @field_validator("tag_mac", mode="before")
    @classmethod
    def validate_tag_mac_format(cls, v: str | None) -> str | None:
        """Валидация формата MAC адреса"""
        if not v:
            return None
        v = v.strip()
        if not v:
            return None
        # Поддерживаем форматы: XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX или XXXXXXXXXXXX
        mac_pattern = re.compile(
            r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$",
        )
        if not mac_pattern.match(v):
            raise ValueError(
                "MAC адрес должен быть в формате XX:XX:XX:XX:XX:XX или XX-XX-XX-XX-XX-XX",
            )
        # Нормализуем к формату с двоеточиями
        v_clean = v.replace("-", "").replace(":", "").upper()
        return ":".join([v_clean[i : i + 2] for i in range(0, 12, 2)])

    @model_validator(mode="after")
    def set_fields_from_aliases(self):
        """Преобразует старые поля в новые для обратной совместимости"""
        # Преобразуем beacon_mac в tag_mac
        if self.beacon_mac and not self.tag_mac:
            self.tag_mac = self.beacon_mac

        # Преобразуем beacon_id или point_id в tag_name
        if (self.beacon_id or self.point_id) and not self.tag_name:
            self.tag_name = self.beacon_id or self.point_id

        return self


class APITagResponseModel(APITagBaseModel):
    """Модель для ответа на запрос метки"""

    id: int
    place: APIPlaceTagResponseModel | None

    # Computed fields для обратной совместимости с frontend
    x: float | None = Field(None, description="Canvas координата X из place.location")
    y: float | None = Field(None, description="Canvas координата Y из place.location")
    z: float | None = Field(None, description="Высота из place.horizon.height")
    horizon_id: int | None = Field(None, description="ID горизонта из place.horizon_id")
    name: str | None = Field(None, description="Название места")
    point_type: str | None = Field(None, description="Тип места")
    point_id: str | None = Field(None, description="tag_name для обратной совместимости")
    beacon_id: str | None = Field(None, description="tag_name для обратной совместимости")
    beacon_mac: str | None = Field(None, description="tag_mac для обратной совместимости")
    beacon_place: str | None = Field(None, description="Название места")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Создаем экземпляр с computed полями"""
        data = super().from_orm(obj).__dict__

        # Заполняем computed поля из place
        if obj.place:
            place = obj.place
            data["name"] = place.name
            data["point_type"] = (
                place.type.value if hasattr(place.type, "value") else str(place.type)
            )
            data["horizon_id"] = place.horizon_id

            # Координаты из geometry
            # Примечание: координаты должны быть извлечены в запросе через ST_X/ST_Y
            # Если координаты не были загружены в запросе, они будут None
            # Это нормально, так как from_orm - синхронный метод и не может выполнять SQL запросы
            x_coord = None
            y_coord = None
            if hasattr(place, "_x_coord") and hasattr(place, "_y_coord"):
                x_coord = place._x_coord
                y_coord = place._y_coord
            elif hasattr(place, "geometry") and place.geometry:
                # Если geometry есть, но координаты не были извлечены в запросе,
                # устанавливаем None (координаты должны извлекаться в запросе через ST_X/ST_Y)
                x_coord = None
                y_coord = None

            data["x"] = x_coord
            data["y"] = y_coord

            # Создаем location для place (для обратной совместимости)
            # x_coord и y_coord из ST_X/ST_Y - это GPS координаты (lon, lat)
            # Фронтенд ожидает формат {'lon': lon, 'lat': lat} или {'x': lon, 'y': lat}
            location = None
            if x_coord is not None and y_coord is not None:
                # Используем формат {'lon': lon, 'lat': lat} для совместимости с getPlaceLonLat
                location = {"lon": x_coord, "lat": y_coord}

            data["place"] = APIPlaceTagResponseModel(
                name=place.name,
                type=place.type,
                location=location,
            )

            # Высота из horizon (не используем @hybrid_property из-за синхронного контекста)
            data["z"] = place.horizon.height if place.horizon else 0.0

            data["beacon_place"] = place.name

        # Обратная совместимость
        data["point_id"] = obj.tag_name
        data["beacon_id"] = obj.tag_name
        data["beacon_mac"] = obj.tag_mac

        return cls(**data)


class APITagsResponseModel(APIBaseModel):
    """Модель для ответа на запрос списка меток"""

    page: int = 1
    pages: int
    size: int = 10
    total: int
    items: list[APITagResponseModel] = Field(..., description="Список меток")
