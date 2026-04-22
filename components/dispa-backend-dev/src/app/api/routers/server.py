"""API endpoints для server mode - управление всеми машинами.

Предоставляет endpoints для получения данных по всем машинам
с возможностью фильтрации по конкретной машине.
"""

from datetime import datetime
from typing import Any

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import desc, func, select

from app.api.schemas.common import PaginatedResponse
from app.api.schemas.tasks.route_tasks import RouteTaskResponse
from app.api.schemas.trips import CycleAnalyticsResponse
from app.database.models import (
    Cycle,
    CycleAnalytics,
    RouteTask,
)
from app.utils.session import SessionDepends

# Алиас для совместимости
TripAnalyticsResponse = CycleAnalyticsResponse


router = APIRouter(prefix="/server", tags=["server"])


@router.get("/")
async def server_root() -> dict[str, str]:
    """Проверка что server роуты работают."""
    return {"message": "Server API is working", "mode": "server"}


@router.get(
    "/tasks",
    response_model=PaginatedResponse[RouteTaskResponse],
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))],
)
async def get_all_tasks(
    session: SessionDepends,
    vehicle_filter: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
) -> Any:
    """Получить все задания со всех машин с фильтром по vehicle_id.

    Используется в server mode для отображения заданий всех машин.
    """
    try:
        # Базовый запрос
        query = select(RouteTask)

        # Фильтр по машине если указан (через связь с ShiftTask)
        if vehicle_filter and vehicle_filter != "all":
            from app.database.models import ShiftTask

            query = query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                ShiftTask.vehicle_id == int(vehicle_filter),
            )

        # Пагинация
        query = query.offset((page - 1) * size).limit(size)

        # Выполнить запрос
        result = await session.execute(query)
        tasks = result.scalars().all()

        # Подсчитать общее количество
        count_query = select(func.count(RouteTask.id))
        if vehicle_filter and vehicle_filter != "all":
            from app.database.models import ShiftTask

            count_query = count_query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                ShiftTask.vehicle_id == int(vehicle_filter),
            )

        count_result = await session.execute(count_query)
        total = count_result.scalar_one()

        # Рассчитать количество страниц
        pages = (total + size - 1) // size

        logger.info(
            "Server tasks retrieved",
            vehicle_filter=vehicle_filter,
            page=page,
            size=size,
            total=total,
        )

        return PaginatedResponse[RouteTaskResponse](
            items=[RouteTaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    except Exception as e:
        logger.error("Get all tasks error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get(
    "/cycles",
    response_model=PaginatedResponse[dict[str, Any]],
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))],
)
async def get_all_cycles(
    session: SessionDepends,
    vehicle_filter: str | None = Query(None, description="Фильтр по vehicle_id"),
    status_filter: str | None = Query(None, description="Фильтр по статусу цикла"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> Any:
    """Получить все циклы со всех машин с фильтром по vehicle_id и статусу.

    Фильтры:
    - vehicle_filter: конкретный vehicle_id или None (все машины)
    - status_filter: in_progress, completed, cancelled или None (все)
    """
    try:
        query = select(Cycle)

        # Фильтр по машине
        if vehicle_filter and vehicle_filter != "all":
            query = query.where(Cycle.vehicle_id == vehicle_filter)

        # Фильтр по статусу
        if status_filter and status_filter != "all":
            query = query.where(Cycle.cycle_status == status_filter)

        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
        offset = (page - 1) * size
        query = query.order_by(desc(Cycle.created_at)).offset(offset).limit(size)

        result = await session.execute(query)
        cycles = result.scalars().all()

        pages = (total + size - 1) // size if total > 0 else 1

        logger.info(
            "Server cycles retrieved",
            vehicle_filter=vehicle_filter,
            status_filter=status_filter,
            page=page,
            size=size,
            total=total,
        )

        return PaginatedResponse[dict[str, Any]](
            items=[
                {
                    "cycle_id": cycle.cycle_id,
                    "vehicle_id": cycle.vehicle_id,
                    "task_id": cycle.task_id,
                    "shift_task_id": cycle.shift_id,
                    "from_place_id": cycle.from_place_id,
                    "to_place_id": cycle.to_place_id,
                    "cycle_started_at": cycle.cycle_started_at,
                    "cycle_completed_at": cycle.cycle_completed_at,
                    "cycle_status": cycle.cycle_status,
                    "cycle_type": cycle.cycle_type,
                    "created_at": cycle.created_at,
                }
                for cycle in cycles
            ],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    except Exception as e:
        logger.error("Get all cycles error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get(
    "/analytics",
    response_model=PaginatedResponse[CycleAnalyticsResponse],
    dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))],
)
async def get_all_analytics(
    session: SessionDepends,
    vehicle_filter: str | None = Query(None, description="Фильтр по vehicle_id"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    from_date: datetime | None = Query(None, description="Дата начала периода"),
    to_date: datetime | None = Query(None, description="Дата окончания периода"),
) -> Any:
    """Получить аналитику циклов со всех машин с фильтром.

    Фильтры:
    - vehicle_filter: конкретный vehicle_id или None (все машины)
    - from_date, to_date: период по created_at
    """
    try:
        query = select(CycleAnalytics)

        # Фильтр по машине
        if vehicle_filter and vehicle_filter != "all":
            query = query.where(CycleAnalytics.vehicle_id == vehicle_filter)

        # Фильтр по дате
        if from_date:
            query = query.where(CycleAnalytics.created_at >= from_date)
        if to_date:
            query = query.where(CycleAnalytics.created_at <= to_date)

        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Пагинация
        offset = (page - 1) * size
        query = query.order_by(desc(CycleAnalytics.created_at)).offset(offset).limit(size)

        result = await session.execute(query)
        analytics = result.scalars().all()

        pages = (total + size - 1) // size if total > 0 else 1

        logger.info(
            "Server analytics retrieved",
            vehicle_filter=vehicle_filter,
            page=page,
            size=size,
            total=total,
        )

        return PaginatedResponse[CycleAnalyticsResponse](
            items=[CycleAnalyticsResponse.model_validate(item) for item in analytics],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    except Exception as e:
        logger.error("Get all analytics error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
