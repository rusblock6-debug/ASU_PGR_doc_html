"""Схемы для тултипа по технике на карте."""

from pydantic import Field

from app.api.schemas.base import APIBaseModel


class VehicleTooltipResponse(APIBaseModel):
    """Ответ для тултипа состояния техники."""

    state: str = Field(
        ...,
        description="Системное имя последнего статуса (state machine); при отсутствии данных — no_data",
    )
    state_duration: int | None = Field(
        None,
        description="Длительность последнего статуса (сек); null если статус не определён",
    )
    actual_trips_count: int | None = Field(
        None,
        description="Выполнено рейсов по активному НЗ в текущей смене; null если не применимо",
    )
    planned_trips_count: int | None = Field(
        None,
        description="План рейсов по активному НЗ в текущей смене; null если не применимо",
    )
    weight: float | None = Field(
        None,
        description="Вес (tonnes) из telemetry-service; null если нет данных в стриме",
    )
    speed: float | None = Field(
        None,
        description="Скорость (km/h) из telemetry-service; null если нет данных в стриме",
    )
    place_name: str | None = Field(None, description="Название места из graph-service; null если нет данных")
    last_message_timestamp: str | None = Field(
        None,
        description=(
            "Время последнего сообщения в стримах telemetry-service (gps, speed, weight), "
            "UTC в формате YYYY-MM-DDTHH:MM:SSZ (без дробной части секунд); null если нет данных"
        ),
    )
