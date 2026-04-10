"""Pydantic модели для graph-service"""

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.enum.places import PlaceTypeEnum
from app.schemas.base import APIBaseModel
from app.schemas.common import TimestampBase


class PlaceBase(BaseModel):
    """Базовая модель места (общая для всех типов: load, unload, reload, transit, park)"""

    name: str
    type: PlaceTypeEnum  # 'load', 'unload', 'reload', 'transit', 'park'
    node_id: int | None = Field(None, description="ID узла графа")
    cargo_type: int | None = Field(None, description="Идентификатор вида груза")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PlaceCreateBase(PlaceBase):
    """Базовые поля для создания места."""

    id: int | None = Field(
        None,
        description="ID места (опционально, для синхронизации с сервером)",
    )


class LoadPlaceCreate(PlaceCreateBase):
    """Схема создания места типа load."""

    type: Literal[PlaceTypeEnum.load]
    start_date: date = Field(..., description="Дата начала")
    end_date: date | None = Field(None, description="Дата окончания")
    current_stock: float | None = Field(None, description="Текущий запас")


class UnloadPlaceCreate(PlaceCreateBase):
    """Схема создания места типа unload."""

    type: Literal[PlaceTypeEnum.unload]
    start_date: date = Field(..., description="Дата начала")
    end_date: date | None = Field(None, description="Дата окончания")
    capacity: float | None = Field(None, description="Вместимость")
    current_stock: float | None = Field(None, description="Текущий запас")


class ReloadPlaceCreate(PlaceCreateBase):
    """Схема создания места типа reload."""

    type: Literal[PlaceTypeEnum.reload]
    start_date: date = Field(..., description="Дата начала")
    end_date: date | None = Field(None, description="Дата окончания")
    capacity: float | None = Field(None, description="Вместимость")
    current_stock: float | None = Field(None, description="Текущий запас")


class ParkPlaceCreate(PlaceCreateBase):
    """Схема создания места типа park."""

    type: Literal[PlaceTypeEnum.park]


class TransitPlaceCreate(PlaceCreateBase):
    """Схема создания места типа transit."""

    type: Literal[PlaceTypeEnum.transit]


PlaceCreate = Annotated[
    LoadPlaceCreate | UnloadPlaceCreate | ReloadPlaceCreate | ParkPlaceCreate | TransitPlaceCreate,
    Field(discriminator="type"),
]


class PlaceUpdateBase(BaseModel):
    """Базовые поля для частичного обновления места (общие для всех типов)."""

    name: str | None = Field(None, description="Название места")
    type: PlaceTypeEnum | None = Field(
        None,
        description="Тип места: load, unload, reload, transit, park",
    )
    node_id: int | None = Field(None, description="ID узла графа")
    cargo_type: int | None = Field(None, description="Идентификатор вида груза")
    source: str | None = Field(
        None,
        description=(
            "Источник изменения (например: dispatcher, system)."
            " При dispatcher изменения остатков считаются ручными."
        ),
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LoadPlaceUpdate(PlaceUpdateBase):
    """Схема обновления места типа load."""

    type: Literal[PlaceTypeEnum.load]
    start_date: date | None = Field(None, description="Дата начала")
    end_date: date | None = Field(None, description="Дата окончания")
    current_stock: float | None = Field(None, description="Текущий запас")


class UnloadPlaceUpdate(PlaceUpdateBase):
    """Схема обновления места типа unload."""

    type: Literal[PlaceTypeEnum.unload]
    start_date: date | None = Field(None, description="Дата начала")
    end_date: date | None = Field(None, description="Дата окончания")
    capacity: float | None = Field(None, description="Вместимость")
    current_stock: float | None = Field(None, description="Текущий запас")


class ReloadPlaceUpdate(PlaceUpdateBase):
    """Схема обновления места типа reload."""

    type: Literal[PlaceTypeEnum.reload]
    start_date: date | None = Field(None, description="Дата начала")
    end_date: date | None = Field(None, description="Дата окончания")
    capacity: float | None = Field(None, description="Вместимость")
    current_stock: float | None = Field(None, description="Текущий запас")


class ParkPlaceUpdate(PlaceUpdateBase):
    """Схема обновления места типа park."""

    type: Literal[PlaceTypeEnum.park]


class TransitPlaceUpdate(PlaceUpdateBase):
    """Схема обновления места типа transit."""

    type: Literal[PlaceTypeEnum.transit]


PlaceUpdate = Annotated[
    LoadPlaceUpdate | UnloadPlaceUpdate | ReloadPlaceUpdate | ParkPlaceUpdate | TransitPlaceUpdate,
    Field(discriminator="type"),
]


class PlacePatch(PlaceUpdateBase):
    """Тело PATCH /places/{id}: все поля опциональны, `type` не обязателен.

    Для частичных обновлений (например только current_stock + source) тип берётся
    из существующей записи в БД.
    """

    start_date: date | None = Field(None, description="Дата начала")
    end_date: date | None = Field(None, description="Дата окончания")
    capacity: float | None = Field(None, description="Вместимость")
    current_stock: float | None = Field(None, description="Текущий запас")


class PlaceResponseBase(PlaceBase, TimestampBase):
    """Базовые поля ответа (общие для всех типов мест)."""

    id: int
    section_ids: list[int] = Field(
        default_factory=list,
        description="IDs участков через связь места с horizon и section_horizons",
    )

    x: float | None = Field(
        None,
        description="Координата X (Canvas координата или GPS lon, в зависимости от контекста)",
    )
    y: float | None = Field(
        None,
        description="Координата Y (Canvas координата или GPS lat, в зависимости от контекста)",
    )
    location: dict[str, Any] | None = Field(
        None,
        description="Объект location с координатами (для обратной совместимости)",
    )
    horizon_id: int | None = None
    is_active: bool = Field(..., description="Признак активности места")

    # Внутренние поля для GPS координат (используются при сохранении в geometry)
    _gps_lat: float | None = None
    _gps_lon: float | None = None

    model_config = ConfigDict(from_attributes=True)


class LoadPlaceResponse(PlaceResponseBase):
    """Ответ для места типа load (погрузка). Нет capacity."""

    type: Literal[PlaceTypeEnum.load]
    start_date: date | None = None
    end_date: date | None = None
    current_stock: float | None = None


class UnloadPlaceResponse(PlaceResponseBase):
    """Ответ для места типа unload (разгрузка)."""

    type: Literal[PlaceTypeEnum.unload]
    start_date: date | None = None
    end_date: date | None = None
    capacity: float | None = None
    current_stock: float | None = None


class ReloadPlaceResponse(PlaceResponseBase):
    """Ответ для места типа reload (перегрузка)."""

    type: Literal[PlaceTypeEnum.reload]
    start_date: date | None = None
    end_date: date | None = None
    capacity: float | None = None
    current_stock: float | None = None


class ParkPlaceResponse(PlaceResponseBase):
    """Ответ для места типа park (стоянка). Нет операционных полей."""

    type: Literal[PlaceTypeEnum.park]


class TransitPlaceResponse(PlaceResponseBase):
    """Ответ для места типа transit (транзит). Нет операционных полей."""

    type: Literal[PlaceTypeEnum.transit]


PlaceResponse = Annotated[
    LoadPlaceResponse
    | UnloadPlaceResponse
    | ReloadPlaceResponse
    | ParkPlaceResponse
    | TransitPlaceResponse,
    Field(discriminator="type"),
]


class PlaceStockUpdate(BaseModel):
    """Модель для обновления остатков на месте"""

    change_type: str = Field(..., description="Тип изменения: loading, unloading, initial")
    change_amount: float = Field(
        ...,
        description="Величина изменения (signed delta; может быть отрицательной или положительной)",
    )


class PlaceStockUpdateResponse(BaseModel):
    """Ответ на успешное обновление остатков места."""

    status: Literal["ok"]


class PlaceDeleteResponse(APIBaseModel):
    """Ответ на успешное удаление места."""

    id: int
    message: str = Field(..., description="Статусное сообщение")


class PlacesListResponse(APIBaseModel):
    """Ответ списка мест (пагинация/без пагинации)."""

    page: int = Field(..., description="Номер текущей страницы")
    pages: int = Field(..., description="Количество страниц")
    size: int = Field(..., description="Размер страницы")
    total: int = Field(..., description="Общее количество элементов")
    items: list[PlaceResponse] = Field(..., description="Список мест")


class PlacesGroupedItem(APIBaseModel):
    """Группа мест одного типа."""

    type: str = Field(..., description="Тип места")
    count: int = Field(..., description="Количество мест в группе")
    items: list[PlaceResponse] = Field(..., description="Места этого типа")


class PlacesGroupedResponse(APIBaseModel):
    """Ответ списка мест, сгруппированного по типам."""

    total: int = Field(..., description="Общее количество мест")
    groups: list[PlacesGroupedItem] = Field(..., description="Группы по типам")


class PlacesPopupResponse(APIBaseModel):
    """Модель для ответа при вызове модального окна на карте"""

    cargo_type: int | None = Field(None, description="Идентификатор вида груза")
    current_stock: float | None = Field(None, description="Текущий остаток")
    planned_value: float | None = Field(None, description="Плановое значение груза")
    real_value: float | None = Field(None, description="Фактическое значение груза")
    vehicle_id_list: list[int] | None = Field(None, description="Список id техники в зоне")
