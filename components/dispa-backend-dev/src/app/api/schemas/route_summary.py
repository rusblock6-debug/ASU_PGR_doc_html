"""Pydantic-схемы для сводки маршрутов (Route Summary).

Используются эндпоинтом GET /api/route-summary для отображения
агрегированных данных по уникальным маршрутам текущей смены.
"""

from pydantic import BaseModel, Field


class RouteSummaryItem(BaseModel):
    """Агрегированные данные по одному уникальному маршруту."""

    place_a_id: int = Field(..., description="ID места погрузки (ПП)")
    place_b_id: int = Field(..., description="ID места разгрузки (ПР)")
    volume_plan: float = Field(
        ...,
        description="Суммарный плановый объём по всем наряд-заданиям маршрута",
    )
    volume_fact: float = Field(
        ...,
        description="Фактический перевезённый объём (из place_remaining_history)",
    )
    active_vehicles: list[int] = Field(
        default_factory=list,
        description="ID техники в статусе ACTIVE на данном маршруте",
    )
    pending_vehicles: list[int] = Field(
        default_factory=list,
        description="ID техники, назначенной диспетчером на этот маршрут (pending)",
    )
    route_task_ids: list[str] = Field(
        default_factory=list,
        description="ID наряд-заданий, составляющих этот маршрут",
    )


class RouteSummaryResponse(BaseModel):
    """Ответ эндпоинта route-summary."""

    shift_date: str | None = Field(None, description="Дата смены")
    shift_num: int | None = Field(None, description="Номер смены")
    routes: list[RouteSummaryItem] = Field(
        default_factory=list,
        description="Список уникальных маршрутов",
    )


class FleetVehicle(BaseModel):
    """Техника в рамках fleet-control ответа."""

    id: int = Field(..., description="ID техники")
    name: str = Field(..., description="Имя техники (из enterprise-service)")
    state: str = Field(..., description="Текущее state техники из cycle_state_history")
    is_assigned: bool = Field(..., description="Признак active/pending в рамках текущего контекста")
    vehicle_type: str = Field(..., description="Тип техники (vehicle.vehicle_type из enterprise-service)")


class FleetRouteSummaryItem(BaseModel):
    """Единый объект маршрута для fleet-control."""

    place_a_id: int = Field(..., description="ID места погрузки (ПП)")
    place_b_id: int = Field(..., description="ID места разгрузки (ПР)")
    route_id: str = Field(..., description="route_id = place_a_id + '-' + place_b_id")
    section_ids: list[int] = Field(
        default_factory=list,
        description="Список section_ids для маршрута (place_a_id → horizon → sections)",
    )

    volume_plan: float = Field(
        ...,
        description="Суммарный плановый объём по всем наряд-заданиям маршрута",
    )
    volume_fact: float = Field(
        ...,
        description="Фактический перевезённый объём (из place_remaining_history)",
    )
    vehicles: list[FleetVehicle] = Field(
        ...,
        description="Техника на маршруте (active/pending различаются по is_assigned)",
    )
    route_task_ids: list[str] = Field(
        default_factory=list,
        description="ID наряд-заданий, составляющих этот маршрут",
    )
    route_length_m: float | None = Field(
        None,
        description="Длина маршрута ПП→ПР по графу (метры), из graph-service /api/route/{start}/{target}",
    )


class FleetControlRouteItem(BaseModel):
    """Упрощенный объект маршрута для UI на странице fleet-control."""

    route_id: str = Field(..., description="route_id = place_a_id + '-' + place_b_id")
    place_a_id: int = Field(..., description="ID места погрузки (ПП)")
    place_b_id: int = Field(..., description="ID места разгрузки (ПР)")


class FleetGarageItem(BaseModel):
    """Гараж в ответе fleet-control."""

    id: int = Field(..., description="ID места-гаража (place.id, type=park)")
    name: str = Field(..., description="Название гаража")
    vehicles: list[FleetVehicle] = Field(..., description="Техника, относящаяся к гаражу")


class FleetControlResponse(BaseModel):
    """Единый ответ для страницы управления техникой (fleet-control).

    Объединяет /route-summary и /route-summary/unused-vehicles в один запрос.
    """

    shift_date: str | None = Field(None, description="Дата смены")
    shift_num: int | None = Field(None, description="Номер смены")
    routes: list[FleetRouteSummaryItem] = Field(default_factory=list, description="Список уникальных маршрутов")

    # Unused vehicles (бывший /unused-vehicles)
    no_task: list[FleetVehicle] = Field(
        default_factory=list,
        description="Техника без активного задания (is_assigned=true)",
    )
    # Схлопнутые гаражи + pending_garage, pending различаем по is_assigned=true в элементах техники.
    garages: list[FleetGarageItem] = Field(
        default_factory=list,
        description="Список гаражей (включая пустые) и техника по каждому гаражу",
    )
    idle: list[FleetVehicle] = Field(default_factory=list, description="Техника в простое (is_assigned=true)")


class RouteTemplateCreateRequest(BaseModel):
    """Запрос на создание пустого маршрута (шаблона) для текущей смены."""

    place_a_id: int = Field(..., description="ID места погрузки (ПП)")
    place_b_id: int = Field(..., description="ID места разгрузки (ПР)")


class RouteTemplateUpdateRequest(BaseModel):
    """Запрос на изменение ПП/ПР существующего маршрута в текущей смене."""

    from_place_a_id: int = Field(..., description="Текущий ID места погрузки (ПП)")
    from_place_b_id: int = Field(..., description="Текущий ID места разгрузки (ПР)")
    to_place_a_id: int = Field(..., description="Новый ID места погрузки (ПП)")
    to_place_b_id: int = Field(..., description="Новый ID места разгрузки (ПР)")


class RouteTemplateResponse(BaseModel):
    """Результат операций с маршрутными шаблонами."""

    success: bool = Field(..., description="Результат операции")
    message: str = Field(..., description="Описание результата")


class DispatcherAssignmentCreateRequest(BaseModel):
    """Создать/обновить назначение диспетчером для текущей смены."""

    vehicle_id: int = Field(..., description="ID техники")
    source_kind: str = Field(..., description="ROUTE | NO_TASK | GARAGE")
    source_route_place_a_id: int | None = Field(None, description="ПП источника, если source_kind=ROUTE")
    source_route_place_b_id: int | None = Field(None, description="ПР источника, если source_kind=ROUTE")
    source_garage_place_id: int | None = Field(None, description="ID park-места источника, если source_kind=GARAGE")

    target_kind: str = Field(..., description="ROUTE | GARAGE | NO_TASK")
    target_route_place_a_id: int | None = Field(None, description="ПП цели, если target_kind=ROUTE")
    target_route_place_b_id: int | None = Field(None, description="ПР цели, если target_kind=ROUTE")
    target_garage_place_id: int | None = Field(None, description="ID park-места цели, если target_kind=GARAGE")


class DispatcherAssignmentResponse(BaseModel):
    """Назначение диспетчером."""

    id: int = Field(..., description="ID назначения")
    vehicle_id: int
    shift_date: str
    shift_num: int
    source_kind: str
    source_route_place_a_id: int | None = None
    source_route_place_b_id: int | None = None
    source_garage_place_id: int | None = None
    target_kind: str
    target_route_place_a_id: int | None = None
    target_route_place_b_id: int | None = None
    target_garage_place_id: int | None = None
    status: str


class DispatcherAssignmentDecisionRequest(BaseModel):
    """Решение борта по назначению."""

    approved: bool = Field(..., description="true — подтвердить, false — отклонить")


class UnusedVehiclesResponse(BaseModel):
    """Незадействованная техника текущей смены (нет активного наряд-задания)."""

    no_task: list[int] = Field(
        default_factory=list,
        description="ID техники без активного задания (ни одного route_task в ACTIVE)",
    )
    garages: dict[int, list[int]] = Field(
        default_factory=dict,
        description="Техника по каждому гаражу (key = park place_id) по последнему месту (last_place_id)",
    )
    pending_garages: dict[int, list[int]] = Field(
        default_factory=dict,
        description="Pending-назначения диспетчера по каждому гаражу (key = park place_id)",
    )
    idle: list[int] = Field(
        default_factory=list,
        description="ID техники, текущее состояние которой не is_work_status",
    )
