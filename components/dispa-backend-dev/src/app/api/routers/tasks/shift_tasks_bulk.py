"""API endpoints для bulk операций с shift_tasks."""

from typing import Any

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.api.schemas.tasks.shift_tasks_bulk import ShiftTaskBulkUpsertRequest
from app.services.tasks.shift_task_bulk import ShiftTaskBulkService
from app.utils.session import SessionDepends

router = APIRouter(prefix="/shift-tasks", tags=["shift-tasks"])


@router.post("/bulk-upsert", dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))])
async def bulk_upsert_shift_tasks(
    request: ShiftTaskBulkUpsertRequest,
    session: SessionDepends,
) -> Any:
    """Массовое создание/обновление shift_tasks с вложенными route_tasks.

    Логика:
    - Items с id → UPDATE shift_task + route_tasks (UPDATE/CREATE/DELETE)
    - Items без id → CREATE shift_task + route_tasks (только CREATE)

    DELETE route_tasks происходит ТОЛЬКО при UPDATE shift_task.

    Одна транзакция для всех операций (ROLLBACK при ошибке).

    Responses:
        200: Успешно обработано
        400: Ошибка валидации
        500: Ошибка сервера
    """
    try:
        result = await ShiftTaskBulkService.bulk_upsert(
            data=request,
            db=session,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Bulk upsert error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk upsert failed: {str(e)}",
        ) from e
