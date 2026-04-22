"""Pydantic-схемы для транспортных средств (vehicles)."""

from pydantic import ConfigDict, Field, RootModel

from app.schemas.base import APIBaseModel


class VehiclePlaceItem(APIBaseModel):
    """Схема элемента списка мест и горизонтов по подвижному оборудованию."""

    horizon_id: int = Field(..., description="ID горизонта")
    place_id: int = Field(..., description="ID места")
    vehicle_id: int = Field(..., description="ID транспортного средства")


class VehiclePlacesListResponse(APIBaseModel):
    """Схема ответа, содержащего список мест и горизонтов по подвижному оборудованию."""

    items: list[VehiclePlaceItem] = Field(
        default_factory=list,
        description="Список мест и горизонтов по подвижному оборудованию",
    )


class VehicleStatusItem(APIBaseModel):
    """Схема элемента списка status по подвижному оборудованию."""

    vehicle_id: int = Field(..., description="ID транспортного средства")
    status: str = Field(..., description="Состояние")


class VehicleStatusListResponse(APIBaseModel):
    """Схема ответа со списком status по подвижному оборудованию."""

    items: list[VehicleStatusItem] = Field(
        default_factory=list,
        description="Список status по подвижному оборудованию",
    )


class VehicleStateEvent(APIBaseModel):
    """Элемент SSE-потока /stream/vehicles — текущее состояние ТС."""

    event_type: str = Field("vehicle_state", description="Тип события")
    vehicle_id: int = Field(..., description="ID транспортного средства")
    state: str | None = Field(None, description="Текущий статус ТС")
    horizon_id: int | None = Field(None, description="ID горизонта")
    place_id: int | None = Field(None, description="ID последнего тега/места")


class VehicleStateEventList(RootModel[list[VehicleStateEvent]]):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                [
                    {
                        "event_type": "vehicle_state",
                        "vehicle_id": 17,
                        "state": "loading",
                        "horizon_id": 2,
                        "place_id": 42,
                    },
                    {
                        "event_type": "vehicle_state",
                        "vehicle_id": 23,
                        "state": "moving",
                        "horizon_id": 1,
                        "place_id": None,
                    },
                ],
            ],
        },
    )


class VehiclePopupResponse(APIBaseModel):
    """Модель для ответа при вызове модального окна на карте"""

    status_system_name: str | None = Field(..., description="Системное название статуса")
    place_start_id: int | None = Field(None, description="Место начала маршрута")
    place_finish_id: int | None = Field(None, description="Место конца маршрута")
    planned_trips_count: int | None = Field(None, description="Плановое количество рейсов")
    actual_trips_count: int | None = Field(None, description="Фактическое количество рейсов")
    weight: float | None = Field(..., description="Вес")
    speed: float | None = Field(..., description="Скорость")
    current_places_id: int | None = Field(..., description="Текущее место положения")
