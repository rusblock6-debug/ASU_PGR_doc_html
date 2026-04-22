"""Pydantic модели для graph-service"""

from pydantic import BaseModel, Field


class Point(BaseModel):
    """Географическая точка с широтой и долготой."""

    lat: float = Field(..., description="Широта")
    lon: float = Field(..., description="Долгота")


class LocationRequest(Point):
    """Запрос на определение ближайшей метки"""

    height: float | None = Field(None, description="Высота")


class LocationResponse(BaseModel):
    """Ответ с информацией о ближайшей метке (упрощенный формат для eKuiper)"""

    tag_id: int | None = Field(None, description="ID тега в БД")
    tag_name: str | None = Field(
        None,
        description="Имя тега (tag.tag_name, null если метка не найдена)",
    )
    place_id: int | None = Field(
        None,
        description="ID места (place.id, null если место не привязано)",
    )
    place_name: str | None = Field(None, description="Название точки")
    place_type: str | None = Field(None, description="Тип точки")


class RouteGeoJSON(BaseModel):
    """GeoJSON LineString, представляющий маршрут."""

    type: str = Field(..., description="Тип GeoJSON, всегда 'LineString'")
    coordinates: list[list[float]] = Field(
        ...,
        description="Список точек маршрута в формате [долгота, широта]",
    )


class RouteNodesResponse(BaseModel):
    """Информация о построенном маршруте."""

    start_node_id: int = Field(..., description="ID стартовой точки маршрута")
    target_node_id: int = Field(..., description="ID конечной точки маршрута")
    route_geojson: RouteGeoJSON = Field(
        ...,
        description="GeoJSON LineString, представляющий маршрут",
    )
    total_length_m: float = Field(..., description="Длина маршрута в метрах")
    edge_ids: list[int] = Field(..., description="ID точек через которые построен маршрут")


class TimeDataResponse(BaseModel):
    total_seconds: float = Field(..., description="Общее количество секунд")
    formatted: str = Field(..., description="Форматированное время")
    hours: int = Field(..., description="Кол-во полных часов")
    minutes: int = Field(..., description="Кол-во полных минут")
    seconds: int = Field(..., description="Кол-во полных секунд")


class RouteProgressResponse(RouteNodesResponse):
    """Полная информация о текущем состоянии маршрута."""

    user_location: Point = Field(
        ...,
        description="Географическая точка пользователя с широтой и долготой",
    )
    nearest_point_on_route: Point | None = Field(
        None,
        description="Ближайшая точка на маршруте. Если deviation_detected = true, то null.",
    )
    distance_covered_m: float = Field(..., description="Пройденное расстояние маршрута в метрах")
    distance_remaining_m: float = Field(..., description="Оставшиеся расстояние маршрута в метрах")
    percent_complete: float = Field(..., description="Оставшиеся расстояние маршрута в %")
    deviation_detected: bool = Field(..., description="Флаг отклонения маршрута")
    new_route: bool = Field(..., description="Флаг создания нового маршрута")
    time_data: TimeDataResponse | None
