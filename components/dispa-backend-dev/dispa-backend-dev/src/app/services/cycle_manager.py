"""Cycle Manager - управление циклами работы техники.

Cycle (цикл) - полный цикл работы техники от начала движения порожним до разгрузки:
moving_empty → stopped_empty → loading → moving_loaded → stopped_loaded → unloading

Цикл может содержать рейс (Trip), или может быть без рейса (ремонтный цикл).
"""

from datetime import UTC, datetime
from typing import Any, cast

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models import Cycle
from app.services.analytics import finalize_cycle_analytics
from app.services.trip_event_publisher import publish_trip_event
from app.utils import truncate_datetime_to_seconds


async def create_cycle(
    vehicle_id: int,
    from_place_id: int | None = None,
    task_id: str | None = None,
    shift_id: str | None = None,
    cycle_type: str = "normal",
    db: AsyncSession | None = None,
    start_time: datetime | None = None,
) -> str:
    """Создать новый цикл работы техники.

    Вызывается при переходе в состояние moving_empty.

    Args:
        vehicle_id: ID транспортного средства
        from_place_id: ID места начала цикла (place.id из graph-service)
        task_id: ID активного задания
        shift_id: ID активной смены
        cycle_type: Тип цикла (normal, repair, maintenance, refueling)
        db: Database session
        start_time: Время начала цикла (опционально)

    Returns:
        cycle_id: ID созданного цикла

    Note:
        entity_type устанавливается автоматически в 'cycle' (JTI discriminator).
        При создании Trip из Cycle, entity_type изменится на 'trip'.
    """
    if not db:
        raise ValueError("Database session is required")

    # Создать новый цикл.
    if start_time is not None:
        effective_start_time = start_time
    else:
        effective_start_time = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))
    cycle = Cycle(
        vehicle_id=vehicle_id,
        task_id=task_id,
        shift_id=shift_id,
        from_place_id=from_place_id,
        cycle_started_at=effective_start_time,
        cycle_status="in_progress",
        cycle_type=cycle_type,
    )

    db.add(cycle)
    await db.flush()  # Получить ID не коммитя транзакцию

    logger.info(
        "Cycle created",
        vehicle_id=vehicle_id,
        cycle_id=cycle.cycle_id,
        from_place_id=from_place_id,
        task_id=task_id,
        cycle_type=cycle.cycle_type,
    )

    try:
        await publish_trip_event(
            event_type="cycle_started",
            cycle_id=cycle.cycle_id,
            server_trip_id=task_id,
            trip_type=None,
            vehicle_id=str(vehicle_id),
            place_id=from_place_id or 0,
            state="moving_empty",
            shift_id=shift_id,
            event_timestamp=effective_start_time,
        )
    except Exception as e:
        logger.error(
            "Failed to publish cycle_started event",
            cycle_id=cycle.cycle_id,
            vehicle_id=vehicle_id,
            error=str(e),
            exc_info=True,
        )

    return cycle.cycle_id


async def complete_cycle(
    cycle_id: str,
    to_place_id: int | None = None,
    db: AsyncSession | None = None,
    end_time: datetime | None = None,
    unloading_timestamp: datetime | None = None,
    place_remaining_change: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Завершить цикл.

    Вызывается после завершения unloading.

    Args:
        cycle_id: ID цикла
        to_place_id: ID места завершения цикла (place.id из graph-service)
        db: Database session
        end_time: Время завершения цикла (опционально)
        unloading_timestamp: Время начала разгрузки (опционально)
        place_remaining_change: Данные об изменении остатка места (опционально)

    Returns:
        dict с результатом:
        - success: bool
        - message: str
        - cycle: Cycle (если найден)
    """
    if not db:
        return {"success": False, "message": "Database session is required"}

    # Найти цикл
    result = await db.execute(
        select(Cycle).where(Cycle.cycle_id == cycle_id),
    )
    cycle = result.scalar_one_or_none()

    if not cycle:
        logger.error(
            "Cycle not found",
            cycle_id=cycle_id,
        )
        return {
            "success": False,
            "message": f"Cycle {cycle_id} not found",
        }

    # Обновить цикл.
    if end_time is not None:
        effective_end_time = end_time
    else:
        effective_end_time = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))
    cycle.cycle_completed_at = effective_end_time
    cycle.to_place_id = to_place_id
    cycle.cycle_status = "completed"

    await db.commit()

    # Вычислить длительность цикла с обработкой timezone
    duration_seconds = None
    if cycle.cycle_started_at and cycle.cycle_completed_at:
        try:
            duration_seconds = (cycle.cycle_completed_at - cycle.cycle_started_at).total_seconds()
        except TypeError:
            # Если один из timestamp-ов без timezone, добавляем UTC
            start_time = (
                cycle.cycle_started_at if cycle.cycle_started_at.tzinfo else cycle.cycle_started_at.replace(tzinfo=UTC)
            )
            end_time = (
                cycle.cycle_completed_at
                if cycle.cycle_completed_at.tzinfo
                else cycle.cycle_completed_at.replace(tzinfo=UTC)
            )
            duration_seconds = (end_time - start_time).total_seconds()

    # Вычислить и сохранить аналитику цикла (на сервере и на борту)
    try:
        analytics_result = await finalize_cycle_analytics(cycle_id, db)
        if analytics_result:
            logger.info(
                "Cycle analytics saved",
                cycle_id=cycle_id,
                service_mode=settings.service_mode,
                total_duration=analytics_result.get("total_cycle_duration_seconds"),
            )
        else:
            logger.warning(
                "Failed to calculate cycle analytics",
                cycle_id=cycle_id,
            )
    except Exception as e:
        logger.error(
            "Error calculating cycle analytics",
            cycle_id=cycle_id,
            error=str(e),
            exc_info=True,
        )

    try:
        await publish_trip_event(
            event_type="cycle_completed",
            cycle_id=cycle_id,
            server_trip_id=cycle.task_id,
            trip_type=None,
            vehicle_id=str(cycle.vehicle_id),
            place_id=to_place_id or 0,
            state="unloading",
            event_timestamp=effective_end_time,
            unloading_timestamp=unloading_timestamp,
            place_remaining_change=place_remaining_change,
        )
    except Exception as e:
        logger.error(
            "Failed to publish cycle_completed event",
            cycle_id=cycle_id,
            vehicle_id=cycle.vehicle_id,
            error=str(e),
            exc_info=True,
        )

    logger.info(
        "Cycle completed",
        vehicle_id=cycle.vehicle_id,
        cycle_id=cycle_id,
        to_place_id=to_place_id,
        duration_seconds=duration_seconds,
    )

    return {
        "success": True,
        "message": f"Cycle {cycle_id} completed successfully",
        "cycle": cycle,
    }


async def get_cycle_by_id(
    cycle_id: str,
    db: AsyncSession,
) -> Cycle | None:
    """Получить цикл по ID.

    Args:
        cycle_id: ID цикла
        db: Database session

    Returns:
        Cycle или None
    """
    result = await db.execute(
        select(Cycle).where(Cycle.cycle_id == cycle_id),
    )
    return result.scalar_one_or_none()


async def get_active_cycle(
    vehicle_id: str,
    db: AsyncSession,
) -> Cycle | None:
    """Получить активный цикл для транспорта.

    Args:
        vehicle_id: ID транспортного средства
        db: Database session

    Returns:
        Cycle или None
    """
    result = await db.execute(
        select(Cycle)
        .where(Cycle.vehicle_id == vehicle_id)
        .where(Cycle.cycle_status == "in_progress")
        .order_by(Cycle.created_at.desc())
        .limit(1),
    )
    return result.scalar_one_or_none()
