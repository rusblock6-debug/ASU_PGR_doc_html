"""API endpoints для bulk операций с route_tasks."""

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.api.schemas.common import BulkResponse
from app.api.schemas.tasks.route_tasks_bulk import (
    RouteTaskBulkUpsertRequest,
    RouteTaskBulkUpsertResponse,
)
from app.services.tasks.route_task_bulk import RouteTaskBulkService
from app.utils.session import SessionDepends

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "/upsert-bulk",
    response_model=RouteTaskBulkUpsertResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def bulk_upsert_route_tasks(
    request: RouteTaskBulkUpsertRequest,
    session: SessionDepends,
) -> BulkResponse:
    """Bulk upsert route tasks (создание + обновление).

    Оптимизированная операция для создания и обновления множества route_tasks за одну транзакцию.

    - id = None → CREATE (генерируется новый ID)
    - id указан → UPDATE (обновляется существующая запись)

    Оптимизации:
    - Одна транзакция для всех операций (один commit)
    """
    try:
        result = await RouteTaskBulkService.bulk_upsert(
            data=request,
            db=session,
            shift_task_id=None,
        )
        return BulkResponse(success=True, count=result.rowcount)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Bulk upsert failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk upsert failed: {str(e)}",
        ) from e
