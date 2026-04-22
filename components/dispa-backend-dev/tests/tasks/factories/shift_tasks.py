"""Фабрики для создания тестовых данных ShiftTask."""

from typing import Any

from app.api.schemas.tasks.shift_tasks_bulk import ShiftTaskUpsertItem
from app.enums import ShiftTaskStatusEnum


def create_shift_task_data(
    work_regime_id: int = 1,
    vehicle_id: int = 1,
    shift_date: str = "2024-01-01",
    shift_num: int = 1,
    status: ShiftTaskStatusEnum = ShiftTaskStatusEnum.PENDING,
    route_tasks: list[dict[str, Any]] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Создать данные для тестового ShiftTask.

    Args:
        work_regime_id: ID режима работы
        vehicle_id: ID транспортного средства
        shift_date: Дата смены (YYYY-MM-DD)
        shift_num: Номер смены
        status: Статус смены
        route_tasks: Список route_tasks (опционально)
        **kwargs: Дополнительные поля

    Returns:
        Dict с данными для создания ShiftTask
    """
    data = {
        "work_regime_id": work_regime_id,
        "vehicle_id": vehicle_id,
        "shift_date": shift_date,
        "shift_num": shift_num,
        "status": status,
        "priority": 0,
        "task_data": None,
        **kwargs,
    }

    if route_tasks is not None:
        data["route_tasks"] = route_tasks

    return data


def create_shift_task_upsert_items(
    count: int = 2,
    with_ids: bool = False,
    **kwargs,
) -> list[ShiftTaskUpsertItem]:
    """Создать список ShiftTaskUpsertItem для тестов.

    Args:
        count: Количество элементов
        with_ids: Если True, половина будет с id (UPDATE), половина без (CREATE)
        **kwargs: Дополнительные параметры

    Returns:
        Список ShiftTaskUpsertItem
    """
    items = []
    for i in range(count):
        item_data = create_shift_task_data(
            vehicle_id=i + 1,
            shift_num=i + 1,
            **kwargs,
        )

        # Если with_ids, то чередуем CREATE и UPDATE
        if with_ids and i % 2 == 1:
            item_data["id"] = f"shift_{i}"

        items.append(ShiftTaskUpsertItem(**item_data))

    return items
