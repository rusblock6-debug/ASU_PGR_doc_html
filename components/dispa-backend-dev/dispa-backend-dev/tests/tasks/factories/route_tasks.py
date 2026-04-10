"""Фабрики для создания тестовых данных RouteTask."""

from typing import Any

from app.api.schemas.tasks.route_tasks_bulk import (
    RouteTaskBulkCreateItem,
    RouteTaskBulkUpdateItem,
    RouteTaskBulkUpsertItem,
)
from app.enums import TripStatusRouteEnum, TypesRouteTaskEnum


def create_route_task_upsert_item_data(
    route_order: int = 0,
    place_a_id: int = 1,
    place_b_id: int = 2,
    type_task: TypesRouteTaskEnum = TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
    planned_trips_count: int = 1,
    status: TripStatusRouteEnum = TripStatusRouteEnum.EMPTY,
    shift_task_id: str | None = "shift_123",
    route_id: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Создать данные для RouteTaskBulkUpsertItem.

    Args:
        route_order: Порядок выполнения
        place_a_id: ID места погрузки
        place_b_id: ID места разгрузки
        type_task: Тип задания
        planned_trips_count: Планируемое количество рейсов
        status: Статус задания
        shift_task_id: ID смены (опционально)
        route_id: ID маршрута (если None, то CREATE, иначе UPDATE)
        **kwargs: Дополнительные поля

    Returns:
        Dict с данными для создания RouteTaskBulkUpsertItem
    """
    data = {
        "route_order": route_order,
        "place_a_id": place_a_id,
        "place_b_id": place_b_id,
        "type_task": type_task,
        "planned_trips_count": planned_trips_count,
        "status": status,
        **kwargs,
    }

    if route_id:
        data["id"] = route_id

    if shift_task_id:
        data["shift_task_id"] = shift_task_id

    return data


def create_route_task_upsert_items(
    count: int = 2,
    with_ids: bool = False,
    **kwargs,
) -> list[RouteTaskBulkUpsertItem]:
    """Создать список RouteTaskBulkUpsertItem для тестов.

    Args:
        count: Количество элементов
        with_ids: Если True, половина будет с id (UPDATE), половина без (CREATE)
        **kwargs: Дополнительные параметры для create_route_task_upsert_item_data

    Returns:
        Список RouteTaskBulkUpsertItem
    """
    items = []
    for i in range(count):
        item_data = create_route_task_upsert_item_data(
            route_order=i,
            place_a_id=i + 1,
            place_b_id=i + 2,
            **kwargs,
        )

        # Если with_ids, то чередуем CREATE и UPDATE
        if with_ids and i % 2 == 1:
            item_data["id"] = f"route_{i}"

        items.append(RouteTaskBulkUpsertItem(**item_data))

    return items


def create_route_task_create_items(
    count: int = 2,
    **kwargs,
) -> list[RouteTaskBulkCreateItem]:
    """Создать список RouteTaskBulkCreateItem для тестов.

    Args:
        count: Количество элементов
        **kwargs: Дополнительные параметры

    Returns:
        Список RouteTaskBulkCreateItem
    """
    items = []
    for i in range(count):
        item_data = create_route_task_upsert_item_data(
            route_order=i,
            place_a_id=i + 1,
            place_b_id=i + 2,
            **kwargs,
        )
        # Убрать id для CREATE
        item_data.pop("id", None)
        items.append(RouteTaskBulkCreateItem(**item_data))

    return items


def create_route_task_update_items(
    count: int = 2,
    **kwargs,
) -> list[RouteTaskBulkUpdateItem]:
    """Создать список RouteTaskBulkUpdateItem для тестов.

    Args:
        count: Количество элементов
        **kwargs: Дополнительные параметры

    Returns:
        Список RouteTaskBulkUpdateItem
    """
    items = []
    for i in range(count):
        item_data = create_route_task_upsert_item_data(
            route_order=i,
            place_a_id=i + 1,
            place_b_id=i + 2,
            route_id=f"route_{i}",  # Обязательно нужен id для UPDATE
            **kwargs,
        )
        items.append(RouteTaskBulkUpdateItem(**item_data))

    return items
