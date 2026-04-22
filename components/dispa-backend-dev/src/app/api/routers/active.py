"""Active RouteTask/Trip API - текущие активные задания и рейсы.

Endpoints:
- GET /api/active-task - Получить активное задание
- DELETE /api/active-task - Очистить активное задание
- GET /api/active-trip - Получить текущий рейс
- PUT /api/active-trip/complete - Завершить рейс вручную
"""

from typing import Any

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.core.config import settings
from app.core.redis_client import redis_client
from app.enums.route_tasks import TripStatusRouteEnum
from app.services.trip_manager import complete_trip
from app.utils.session import SessionDepends

router = APIRouter(prefix="/active", tags=["active"])


# === Active RouteTask Endpoints ===


@router.get("/task", dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))])
async def get_active_task(session: SessionDepends) -> Any:
    """Получить активное задание.

    Returns:
        dict с данными активного задания из PostgreSQL (включая extra_data) или {"task_id": null}
    """
    try:
        # Получить базовые данные из Redis
        task_data = await redis_client.get_active_task(settings.vehicle_id)

        if not task_data:
            return {"task_id": None, "message": "No active task"}

        # Получить полные данные из PostgreSQL (включая extra_data)
        task_id = task_data.get("task_id")
        from sqlalchemy import select

        from app.database.models import RouteTask

        query = select(RouteTask).where(RouteTask.id == task_id)
        result = await session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            # Задание было удалено из БД, но осталось в Redis
            logger.warning(
                "Active task not found in PostgreSQL",
                task_id=task_id,
                vehicle_id=settings.vehicle_id,
            )
            return {"task_id": None, "message": "Active task not found in database"}

        # Вернуть полные данные из PostgreSQL + activated_at из Redis
        return {
            "task_id": task.id,
            "shift_id": task.shift_task_id,  # совместимость со старым фронтом
            "shift_task_id": task.shift_task_id,
            "place_a_id": task.place_a_id,
            "place_b_id": task.place_b_id,
            "order": task.route_order,
            "status": task.status,
            "planned_trips_count": task.planned_trips_count,
            "actual_trips_count": task.actual_trips_count,
            "extra_data": task.route_data or {},
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "activated_at": task_data.get("activated_at"),  # Из Redis
        }

    except Exception as e:
        logger.error("Failed to get active task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения активного задания: {str(e)}",
        ) from e


@router.delete(
    "/task",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.EDIT)))],
)
async def clear_active_task(session: SessionDepends) -> Any:
    """Очистить активное задание (деактивировать).

    - Обновить статус задания в PostgreSQL → 'pending'
    - Удалить из Redis active_task
    - Опубликовать событие task_deactivated
    """
    try:
        # Получить текущее активное задание
        task_data = await redis_client.get_active_task(settings.vehicle_id)

        if not task_data:
            return {"success": True, "message": "No active task to clear"}

        task_id = task_data.get("task_id")

        # Обновить статус в PostgreSQL
        from sqlalchemy import update

        from app.database.models import RouteTask

        query = update(RouteTask).where(RouteTask.id == task_id).values(status=TripStatusRouteEnum.DELIVERED)
        await session.execute(query)
        await session.commit()

        # Удалить из Redis
        await redis_client.delete_active_task(settings.vehicle_id)

        logger.info(
            "Active task cleared",
            vehicle_id=settings.vehicle_id,
            task_id=task_id,
        )

        return {
            "success": True,
            "message": "Active task cleared",
            "task_id": task_id,
        }

    except Exception as e:
        logger.error("Failed to clear active task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка очистки активного задания: {str(e)}",
        ) from e


# === Active Trip Endpoints ===


@router.get(
    "/trip",
    dependencies=[
        Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW), (Permission.TRIP_EDITOR, Action.VIEW))),
    ],
)
async def get_active_trip() -> Any:
    """Получить текущий рейс.

    Возвращает объединенную информацию:
    - active_trip из Redis
    - current_state из State Machine
    - current_tag из Redis
    """
    try:
        # Получить данные из Redis
        trip_data = await redis_client.get_active_trip(settings.vehicle_id)
        state_data = await redis_client.get_state_machine_data(settings.vehicle_id)

        if not trip_data:
            return {
                "cycle_id": None,
                "message": "No active trip",
                "current_state": state_data.get("state") if state_data else None,
            }

        # Объединить информацию
        response = {
            **trip_data,
            "current_state": state_data.get("state") if state_data else None,
            "last_tag_id": state_data.get("last_tag_id") if state_data else None,
            "last_place_id": state_data.get("last_place_id") if state_data else None,
        }

        return response

    except Exception as e:
        logger.error("Failed to get active trip", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения текущего рейса: {str(e)}",
        ) from e


@router.put(
    "/trip/complete",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(require_permission((Permission.WORK_TIME_MAP, Action.EDIT), (Permission.TRIP_EDITOR, Action.EDIT))),
    ],
)
async def complete_active_trip_manually(session: SessionDepends) -> Any:
    """Завершить рейс вручную.

    Вызывает ТУ ЖЕ логику что и при автоматическом завершении:
    - complete_trip() из trip_manager
    - Обновление State Machine (переход в idle)
    - Логирование с пометкой manual=True
    - Публикация событий с пометкой "manual_completion"
    """
    try:
        # Получить данные активного рейса
        trip_data = await redis_client.get_active_trip(settings.vehicle_id)

        if not trip_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Нет активного рейса для завершения",
            )

        cycle_id = trip_data.get("cycle_id")

        # Получить текущее место из State Machine
        state_data = await redis_client.get_state_machine_data(settings.vehicle_id)
        current_place_id = state_data.get("last_place_id") if state_data else None
        current_tag = state_data.get("last_tag_id") if state_data else "manual_complete"

        # Для внеплановых рейсов place_id может быть null - это нормально
        # Просто логируем предупреждение
        if not current_place_id:
            logger.warning(
                "Completing trip without place_id (unplanned trip)",
                vehicle_id=settings.vehicle_id,
                cycle_id=cycle_id,
            )

        # Завершить рейс
        result = await complete_trip(
            vehicle_id=int(settings.vehicle_id),
            cycle_id=str(cycle_id) if cycle_id else "",
            place_id=current_place_id or 0,
            tag=str(current_tag) if current_tag else "manual_complete",
            db=session,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"],
            )

        # Создать аналитику для завершенного рейса
        try:
            from app.services.analytics import finalize_trip_analytics

            await finalize_trip_analytics(str(cycle_id) if cycle_id else "", session)
            logger.info("Analytics created for manually completed trip", cycle_id=cycle_id)
        except Exception as e:
            logger.error(
                "Failed to create analytics for manually completed trip",
                cycle_id=cycle_id,
                error=str(e),
            )

        # Обновить State Machine → переход в idle
        from app.services.state_machine import get_state_machine

        state_machine = get_state_machine(int(settings.vehicle_id))
        current_state_data = await state_machine.get_current_state()
        current_state_data["state"] = "idle"
        current_state_data["cycle_id"] = None
        await redis_client.set_state_machine_data(
            settings.vehicle_id,
            current_state_data,
        )

        logger.info(
            "Trip completed manually",
            vehicle_id=settings.vehicle_id,
            cycle_id=cycle_id,
            manual=True,
        )

        return {
            "success": True,
            "message": "Рейс завершен вручную",
            "cycle_id": cycle_id,
            "trip_type": result.get("trip_type"),
            "task_completed": result.get("task_completed"),
            "task_cancelled": result.get("task_cancelled"),
            "next_task_id": result.get("next_task_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to complete trip manually", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка завершения рейса: {str(e)}",
        ) from e
