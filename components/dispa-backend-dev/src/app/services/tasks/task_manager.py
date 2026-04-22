"""RouteTask Manager - управление заданиями и выбором активного задания.

Основные функции:
- select_next_task() - выбор следующего активного задания
- set_active_task() - установка активного задания
- cancel_task() - отмена задания с выбором следующего
- Управление Redis Sorted Sets для очереди заданий
"""

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client
from app.database.models import RouteTask, ShiftTask
from app.enums.route_tasks import TripStatusRouteEnum


async def select_next_task(
    vehicle_id: str,
    db: AsyncSession,
    current_place_id: int | None = None,
    shift_task_id: str | None = None,
) -> RouteTask | None:
    """Выбрать следующее активное задание.

    Логика выбора:
    1. Первое по order из общей очереди (task_queue:ordered)
    2. Если текущее место НЕ совпадает с place_a_id первого задания →
       ищем задание из текущего места (task_queue:{place_id})
    3. Если нет заданий из текущего места → берем первое по order (холостой пробег)
    4. Если в Redis очереди нет заданий И передан shift_task_id → ищем в PostgreSQL

    Args:
        vehicle_id: ID транспорта
        current_place_id: ID текущего места (place.id из graph-service)
        shift_task_id: ID shift_task для поиска в PostgreSQL (если очередь пуста)
        db: Database session

    Returns:
        RouteTask или None если нет заданий
    """
    try:
        # 1. Получить первое задание по order из общей очереди
        next_task_id = await redis_client.get_next_task_by_order(vehicle_id)

        if not next_task_id:
            logger.info("No tasks in queue", vehicle_id=vehicle_id)

            # Если очередь пуста и передан shift_task_id, ищем в PostgreSQL
            if shift_task_id:
                logger.info(
                    "Searching next task in PostgreSQL",
                    vehicle_id=vehicle_id,
                    shift_task_id=shift_task_id,
                )
                # Ищем следующее задание в том же shift_task со статусом DELIVERED
                query = (
                    select(RouteTask)
                    .join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id)
                    .where(
                        ShiftTask.id == shift_task_id,
                        ShiftTask.vehicle_id == int(vehicle_id),
                        RouteTask.status == TripStatusRouteEnum.DELIVERED,
                    )
                    .order_by(RouteTask.route_order)
                    .limit(1)
                )
                result = await db.execute(query)
                next_task = result.scalar_one_or_none()

                if next_task:
                    logger.info(
                        "Found next task in PostgreSQL",
                        vehicle_id=vehicle_id,
                        task_id=next_task.id,
                        shift_task_id=shift_task_id,
                    )
                    return next_task
                else:
                    logger.info(
                        "No DELIVERED tasks found in PostgreSQL",
                        vehicle_id=vehicle_id,
                        shift_task_id=shift_task_id,
                    )

            return None

        # Загрузить задание из PostgreSQL, со статусом доставлено
        query = select(RouteTask).where(
            RouteTask.id == next_task_id,
            RouteTask.status == TripStatusRouteEnum.DELIVERED,
        )
        result = await db.execute(query)
        next_task = result.scalar_one_or_none()

        if not next_task:
            # Задание не найдено или уже не DELIVERED - удалить из очереди
            await redis_client.remove_task_from_queue(vehicle_id, next_task_id)
            logger.warning(
                "RouteTask not found or not DELIVERED",
                vehicle_id=vehicle_id,
                task_id=next_task_id,
            )
            return None

        # 2. Если текущее место известно и НЕ совпадает с place_a_id задания
        if current_place_id and next_task.place_a_id != current_place_id:
            # Попробовать найти задание из текущего места
            task_from_place_id = await redis_client.get_next_task_by_point(
                vehicle_id,
                str(current_place_id),
            )

            if task_from_place_id:
                # Проверить существование задания, со статусом доставлено
                query = select(RouteTask).where(
                    RouteTask.id == task_from_place_id,
                    RouteTask.status == TripStatusRouteEnum.DELIVERED,
                )
                result = await db.execute(query)
                task_from_place = result.scalar_one_or_none()

                if task_from_place:
                    logger.info(
                        "Selected task from current place",
                        vehicle_id=vehicle_id,
                        task_id=task_from_place.id,
                        place_id=current_place_id,
                    )
                    return task_from_place
                else:
                    # Удалить из очереди
                    await redis_client.remove_task_from_queue(
                        vehicle_id,
                        task_from_place_id,
                    )

        # 3. Вернуть первое задание по order (может потребоваться холостой пробег)
        logger.info(
            "Selected next task by order",
            vehicle_id=vehicle_id,
            task_id=next_task.id,
            start_place=next_task.place_a_id,
            current_place=current_place_id,
        )
        return next_task

    except Exception as e:
        logger.error(
            "Failed to select next task",
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )
        return None


async def set_active_task(
    vehicle_id: str,
    task: RouteTask,
    db: AsyncSession,
) -> dict[str, Any]:
    """Установить задание как активное.

    ВАЖНО: Автоматически приостанавливает предыдущее активное задание!

    - Приостановить предыдущее активное задание (status='paused')
    - UPDATE PostgreSQL: status='active', activated_at=NOW()
    - SET Redis: active_task
    - PUBLISH Redis Pub/Sub: task_activated
    - ZREM из Redis очередей (задание больше не в pending)

    Args:
        vehicle_id: ID транспорта
        task: Задание для активации
        db: Database session

    Returns:
        dict с результатом
    """
    try:
        now = datetime.utcnow()
        # TODO проблема что возможны что когда редис упадет
        #  и потеряет кеш мы не сможем получить активное задание
        # 1. Получить и приостановить предыдущее активное задание
        current_active_data = await redis_client.get_active_task(vehicle_id)
        if current_active_data:
            current_task_id = current_active_data.get("task_id")

            # Не делать ничего, если это то же самое задание
            if current_task_id == task.id:
                logger.info(
                    "RouteTask already active",
                    vehicle_id=vehicle_id,
                    task_id=task.id,
                )
                return {"status": "already_active", "task_id": task.id}

            # Приостановить предыдущее задание в БД
            if current_task_id:
                query = select(RouteTask).where(RouteTask.id == current_task_id)
                result = await db.execute(query)
                current_task = result.scalar_one_or_none()
                if current_task and current_task.status == TripStatusRouteEnum.ACTIVE:
                    current_task.status = TripStatusRouteEnum.PAUSED
                    logger.info(
                        "Previous task PAUSED",
                        vehicle_id=vehicle_id,
                        previous_task_id=current_task_id,
                        new_task_id=task.id,
                    )

        # 2. Обновить статус нового задания в PostgreSQL
        task.status = TripStatusRouteEnum.ACTIVE
        await db.commit()
        await db.refresh(task)

        # TODO сериализация через схему педантик
        # Сохранить в Redis
        task_data = {
            "task_id": task.id,
            "shift_task_id": task.shift_task_id,
            "place_a_id": task.place_a_id,
            "place_b_id": task.place_b_id,
            "order": task.route_order,
            "planned_trips_count": task.planned_trips_count,
            "actual_trips_count": task.actual_trips_count,
            "status": task.status,
            "extra_data": task.route_data or {},
            "activated_at": now.isoformat(),
        }
        await redis_client.set_active_task(vehicle_id, task_data)

        # Удалить из очередей
        await redis_client.remove_task_from_queue(vehicle_id, str(task.id))

        logger.info(
            "RouteTask activated",
            vehicle_id=vehicle_id,
            task_id=task.id,
            shift_task_id=task.shift_task_id,
        )

        return {
            "success": True,
            "message": "RouteTask activated successfully",
            "task_id": task.id,
        }

    except Exception as e:
        logger.error(
            "Failed to activate task",
            vehicle_id=vehicle_id,
            task_id=task.id,
            error=str(e),
            exc_info=True,
        )
        return {"success": False, "message": f"Error: {str(e)}"}


async def cancel_task(
    vehicle_id: str,
    task_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Отменить задание.

    - UPDATE PostgreSQL: status='cancelled', cancelled_at=NOW()
    - Если это активное задание → DEL Redis active_task
    - PUBLISH Redis Pub/Sub: task_cancelled
    - ZREM из Redis очередей
    - Автоматически выбрать следующее задание

    Args:
        vehicle_id: ID транспорта
        task_id: ID задания для отмены
        db: Database session

    Returns:
        dict с результатом и next_task_id
    """
    try:
        # Найти задание
        query = select(RouteTask).where(RouteTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            return {"success": False, "message": "RouteTask not found"}

        # Проверить, активное ли задание
        # Проверяем и в Redis, и по статусу в БД (на случай если Redis упал)
        active_task_data = await redis_client.get_active_task(vehicle_id)
        is_active_in_redis = active_task_data and str(active_task_data.get("task_id")) == task_id
        is_active_in_db = task.status == TripStatusRouteEnum.ACTIVE
        is_active = is_active_in_redis or is_active_in_db

        # Обновить статус в PostgreSQL
        task.status = TripStatusRouteEnum.REJECTED
        await db.commit()

        # Если активное - удалить из Redis
        if is_active:
            await redis_client.delete_active_task(vehicle_id)
            logger.info(
                "Active task REJECTED",
                vehicle_id=vehicle_id,
                task_id=task_id,
                was_in_redis=is_active_in_redis,
                was_in_db=is_active_in_db,
            )
        else:
            # Удалить из очередей
            await redis_client.remove_task_from_queue(vehicle_id, task_id)

        # Автоматически выбрать следующее задание
        next_task_id = None
        if is_active:
            next_task = await select_next_task(
                vehicle_id=vehicle_id,
                current_place_id=None,
                shift_task_id=task.shift_task_id,  # Передаем shift_task_id для поиска в PostgreSQL
                db=db,
            )
            if next_task:
                activation_result = await set_active_task(vehicle_id, next_task, db)
                if activation_result["success"]:
                    next_task_id = next_task.id

        logger.info(
            "RouteTask cancelled",
            vehicle_id=vehicle_id,
            task_id=task_id,
            was_active=is_active,
            next_task_id=next_task_id,
        )

        return {
            "success": True,
            "message": "RouteTask cancelled successfully",
            "task_id": task_id,
            "next_task_id": next_task_id,
        }

    except Exception as e:
        logger.error(
            "Failed to cancel task",
            vehicle_id=vehicle_id,
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        return {"success": False, "message": f"Error: {str(e)}"}
