"""API endpoints для управления историей состояний cycle_state_history.

Предоставляет batch операции и удаление записей cycle_state_history
с соблюдением правил StateMachine.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Body, Depends, Path, Response
from sqlalchemy import select

from app.api.schemas.event_log import (
    CycleStateHistoryBatchRequest,
    CycleStateHistoryBatchResponse,
    StateHistoryDeleteRequest,
    StateHistoryDeleteResponse,
)
from app.database.models import CycleStateHistory
from app.services.dispatcher_event_publisher import publish_dispatcher_event
from app.services.full_shift_state_service import full_shift_state_service
from app.services.state_history_service import (
    batch_upsert_state_history,
    delete_state_history,
    get_last_state_for_vehicle,
)
from app.utils.session import SessionDepends

router = APIRouter(prefix="/cycle-state-history", tags=["cycle-state-history"])


@router.post(
    "/batch",
    response_model=CycleStateHistoryBatchResponse,
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.EDIT)))],
)
async def batch_upsert_vehicle_state_history_endpoint(
    session: SessionDepends,
    request: CycleStateHistoryBatchRequest = Body(...),
) -> Any:
    """Batch создание/редактирование статусов cycle_state_history для транспорта.

    Все операции выполняются в одной транзакции.
    При ошибке в любом элементе - откат всей транзакции.

    Правила создания новых записей:
    - Всегда проверяется что создаваемый статус будет последним (нет более новых записей)
    - При переходе из idle создается новый цикл
    - При переходе из unloading в moving_empty - завершается текущий цикл и создается новый
    - При переходе из unloading в idle - завершается цикл

    Правила редактирования существующих записей (при указании id):
    - Обновляются только timestamp и system_name
    - Все остальные атрибуты (cycle_id и т.д.) сохраняются

    Пример запроса:
    ```json
    {
        "items": [
            {"timestamp": "2025-01-13T10:00:00Z", "system_name": "moving_empty", "system_status": true},
            {"timestamp": "2025-01-13T10:05:00Z", "system_name": "stopped_empty", "system_status": true},
            {"id": "existing-id", "timestamp": "2025-01-13T10:10:00Z", "system_name": "loading", "system_status": false}
        ]
    }
    ```
    """
    items_list = list(request.items) if not isinstance(request.items, list) else request.items

    last_state = await get_last_state_for_vehicle(
        vehicle_id=request.vehicle_id,
        before_timestamp=datetime.now(UTC),
        db=session,
    )
    for item in items_list:
        if item.timestamp is None or (last_state is not None and item.timestamp == last_state.timestamp):
            if hasattr(item, "model_dump"):
                item_payload = item.model_dump(mode="json")
            elif hasattr(item, "__dict__"):
                item_payload = item.__dict__.copy()
            else:
                item_payload = dict(item)

            await publish_dispatcher_event(request.vehicle_id, item_payload)

    result = await batch_upsert_state_history(request.vehicle_id, items_list, session)

    if not result.success:
        return Response(
            content=result.model_dump_json(),
            status_code=400,
            media_type="application/json",
        )

    # Инвалидировать смены для всех затронутых timestamp'ов
    async def invalidate_shifts() -> None:
        for item in items_list:
            if item.timestamp:
                await full_shift_state_service.invalidate_shift_by_timestamp(
                    vehicle_id=request.vehicle_id,
                    timestamp=item.timestamp,
                )

    asyncio.create_task(invalidate_shifts())

    return result


@router.delete(
    "/{record_id}",
    response_model=StateHistoryDeleteResponse,
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.EDIT)))],
)
async def delete_vehicle_state_history_endpoint(
    session: SessionDepends,
    record_id: str = Path(..., description="ID записи для удаления"),
    request: StateHistoryDeleteRequest = Body(...),
) -> Any:
    """Удалить запись cycle_state_history для транспорта.

    При удалении:
    - Очищаются соответствующие поля в Trip:
      - Удаление loading: очищаются loading_place_id, loading_tag, loading_timestamp
      - Удаление unloading: очищаются unloading_place_id, unloading_tag, unloading_timestamp

    Если удаляется первая запись цикла (начало цикла):
    - Без confirm=true вернется ответ с requires_confirmation=true и сообщением
    - С confirm=true удаляется весь цикл и все связанные записи

    Пример использования:
    ```
    # Первый запрос - проверка
    DELETE /api/cycle-history/vehicles/1/state-history/abc123
    Content-Type: application/json

    {
        "confirm": false
    }

    # Ответ если требуется подтверждение:
    {
        "success": false,
        "requires_confirmation": true,
        "message": "Удаление этого статуса приведет к удалению цикла xyz789. Вы уверены?",
        "cycle_id": "xyz789"
    }

    # Подтверждение удаления
    DELETE /api/cycle-history/vehicles/1/state-history/abc123
    Content-Type: application/json

    {
        "confirm": true
    }
    ```
    """
    # Получить запись перед удалением для инвалидации смены
    record_result = await session.execute(
        select(CycleStateHistory).where(CycleStateHistory.id == record_id),
    )
    record = record_result.scalar_one_or_none()

    result = await delete_state_history(record_id, request.confirm, session)

    if not result.success and (result.forbidden or request.confirm):
        return Response(
            content=result.model_dump_json(),
            status_code=400,
            media_type="application/json",
        )

    # Если удаление успешно и запись найдена - инвалидировать смену
    if result.success and record:
        asyncio.create_task(
            full_shift_state_service.invalidate_shift_by_timestamp(
                vehicle_id=record.vehicle_id,
                timestamp=record.timestamp,
            ),
        )

    return result
