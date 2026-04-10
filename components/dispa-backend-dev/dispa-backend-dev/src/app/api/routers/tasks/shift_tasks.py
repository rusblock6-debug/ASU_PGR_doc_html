"""API endpoints для shift_tasks."""

from datetime import date
from typing import Any

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.api.schemas.common import MessageResponse, PaginatedResponse
from app.api.schemas.tasks.shift_tasks import (
    ShiftTaskCreate,
    ShiftTaskResponse,
    ShiftTaskUpdate,
)
from app.enums.route_tasks import TripStatusRouteEnum
from app.services.tasks.shift_task import ShiftTaskService
from app.utils.session import SessionDepends

router = APIRouter(prefix="/shift-tasks", tags=["shift-tasks"])


@router.get(
    "",
    response_model=PaginatedResponse[ShiftTaskResponse],
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def list_shift_tasks(
    session: SessionDepends,
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    status_route_tasks: list[TripStatusRouteEnum] = Query(
        None,
        description="Фильтр по статусу роут тасок",
    ),
    shift_date: str = Query(None, description="Фильтр по дате смены (YYYY-MM-DD)"),
    vehicle_ids: list[int] = Query(None, description="Фильтр по ID транспорта"),
    shift_num: int = Query(None, description="Фильтр по номеру смены"),
) -> Any:
    """Получить список смен с пагинацией.

    Фильтрация:
    - status_route_tasks: active, rejected, sent, delivered, completed, empty, paused
    - shift_date: дата смены в формате YYYY-MM-DD
    - vehicle_id: список ID транспортного средства
    - shift_num: номер смены
    """
    try:
        response_items, total = await ShiftTaskService(session).list_paginated(
            page=page,
            size=size,
            status_route_tasks=status_route_tasks,
            shift_date=shift_date,
            vehicle_ids=vehicle_ids,
            shift_num=shift_num,
        )

        return PaginatedResponse[ShiftTaskResponse].create(
            items=response_items,
            total=total,
            page=page,
            size=size,
        )
    except Exception as e:
        logger.error("List shift tasks error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post(
    "",
    response_model=ShiftTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_shift_task(
    shift_data: ShiftTaskCreate,
    session: SessionDepends,
) -> Any:
    """Создать новую смену с заданиями."""
    try:
        return await ShiftTaskService(session).create(shift_data)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Create shift task error", error=str(e), exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get(
    "/{task_id}",
    response_model=ShiftTaskResponse,
)
async def get_task(
    task_id: str,
    session: SessionDepends,
) -> Any:
    """Получить сменное задание по ID с полной информацией для борта.

    Используется бортом после получения MQTT события об изменении shift_task:
    {"event_type": "entity_changed", "entity_type": "shift_task", "entity_id": "...", "update": "create/update"}

    Борт делает GET запрос и получает полное задание со всеми маршрутами,
    затем либо добавляет его локально, либо обновляет существующее.
    """
    try:
        shift_task = await ShiftTaskService(session).get_by_id(task_id)
        return ShiftTaskResponse.model_validate(shift_task)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Get task error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.put(
    "/{shift_id}",
    response_model=ShiftTaskResponse,
)
async def update_shift_task(
    shift_id: str,
    shift_data: ShiftTaskUpdate,
    session: SessionDepends,
) -> Any:
    """Обновить смену.

    Responses:
        200: Успешно обновлено
        404: Смена не найдена
        500: Ошибка сервера
    """
    try:
        shift_task = await ShiftTaskService(session).update(
            shift_id,
            shift_data,
        )
        return ShiftTaskResponse.model_validate(shift_task)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Update shift task error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.delete(
    "/{shift_id}",
    response_model=MessageResponse,
)
async def delete_shift_task(
    shift_id: str,
    session: SessionDepends,
) -> Any:
    """Удалить смену (мягкое удаление через изменение статуса)."""
    try:
        await ShiftTaskService(session).delete(shift_id)
        return MessageResponse(message=f"Смена {shift_id} успешно удалена")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Delete shift task error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post(
    "/preview-from-previous",
    response_model=list[ShiftTaskResponse],
)
async def preview_shift_tasks_from_previous_shift(
    session: SessionDepends,
    work_regime_id: int = Query(..., description="ID режима работы"),
    target_date: date = Query(..., description="Дата, на которую адаптировать (YYYY-MM-DD)"),
    target_shift_num: int = Query(..., description="Номер смены, на которую адаптировать"),
) -> Any:
    """Получить preview заданий и маршрутов из предыдущей смены с адаптированными датами."""
    try:
        preview_tasks = await ShiftTaskService(session).preview_from_previous_shift(
            work_regime_id=work_regime_id,
            target_date=target_date,
            target_shift_num=target_shift_num,
        )

        return preview_tasks
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Preview from previous shift error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview tasks from previous shift: {str(e)}",
        ) from e
