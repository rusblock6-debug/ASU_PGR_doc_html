"""API endpoints для route_tasks (маршрутные задания)."""

from typing import Annotated

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, Query, status
from loguru import logger

from app.api.exceptions import ServerErrorException
from app.api.schemas.common import MessageResponse, PaginatedResponse
from app.api.schemas.tasks.route_tasks import RouteTaskCreate, RouteTaskResponse, RouteTaskUpdate
from app.core.config import settings
from app.database import RouteTask
from app.enums.route_tasks import TripStatusRouteEnum
from app.services.tasks.route_task import RouteTaskService
from app.utils.session import SessionDepends

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get(
    "",
    response_model=PaginatedResponse[RouteTaskResponse],
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def list_tasks(
    session: SessionDepends,
    page: Annotated[int, Query(ge=1, description="Номер страницы")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Размер страницы")] = 20,
    task_status: Annotated[TripStatusRouteEnum | None, Query(description="Фильтр по статусу")] = None,
    shift_task_id: Annotated[str | None, Query(description="Фильтр по ID смены")] = None,
    vehicle_id: Annotated[int | None, Query(description="Фильтр по vehicle_id (текущая смена)")] = None,
    place_a_id: Annotated[int | None, Query(description="Фильтр по place_a_id")] = None,
    place_b_id: Annotated[int | None, Query(description="Фильтр по place_b_id")] = None,
) -> PaginatedResponse[RouteTaskResponse]:
    """Получить список заданий с пагинацией.

    Фильтрация:
    - shift_task_id: ID смены
    - status: pending, active, completed, cancelled
    """
    try:
        tasks, total = await RouteTaskService(session).list_paginated(
            page=page,
            size=size,
            shift_task_id=shift_task_id,
            status=task_status,
            vehicle_id=vehicle_id,
            place_a_id=place_a_id,
            place_b_id=place_b_id,
        )

        return PaginatedResponse.create(
            items=[RouteTaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            size=size,
        )

    except Exception as e:
        logger.error("List tasks error", error=str(e), exc_info=True)
        raise ServerErrorException() from e


@router.post(
    "",
    response_model=RouteTaskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def create_task(
    task_data: RouteTaskCreate,
    session: SessionDepends,
) -> RouteTask:
    """Создать новое задание."""
    return await RouteTaskService(session).create(route_data=task_data)


@router.get(
    "/{task_id}",
    response_model=RouteTaskResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def get_task(
    task_id: str,
    session: SessionDepends,
) -> RouteTask:
    """Получить задание по ID."""
    return await RouteTaskService(session).get_by_id(route_id=task_id)


@router.put(
    "/{task_id}",
    response_model=RouteTaskResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def update_task(
    task_id: str,
    task_data: RouteTaskUpdate,
    session: SessionDepends,
) -> RouteTask:
    """Обновить задание."""
    return await RouteTaskService(session).update(route_id=task_id, route_data=task_data)


@router.put(
    "/{task_id}/activate",
    response_model=RouteTaskResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def activate_task(
    task_id: str,
    session: SessionDepends,
    vehicle_id: str = settings.vehicle_id,
) -> RouteTask:
    """Активировать задание.

    ВАЖНО: Автоматически приостанавливает предыдущее активное задание!
    Не может быть больше одного активного задания одновременно.
    """
    return await RouteTaskService(session).activate(route_id=task_id, vehicle_id=vehicle_id)


@router.put(
    "/{task_id}/cancel",
    response_model=RouteTaskResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def cancel(
    task_id: str,
    session: SessionDepends,
    vehicle_id: str = settings.vehicle_id,
) -> RouteTask:
    """Отмена задания.

    ВАЖНО: Если задание было активным автоматически активирует другое
    """
    return await RouteTaskService(session).cancel(route_id=task_id, vehicle_id=vehicle_id)


@router.delete(
    "/{task_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def delete_task(
    task_id: str,
    session: SessionDepends,
) -> MessageResponse:
    """Удалить задание (мягкое удаление)."""
    await RouteTaskService(session).delete(route_id=task_id)
    return MessageResponse(
        message=f"Задание {task_id} успешно удалено",
        success=True,
    )
