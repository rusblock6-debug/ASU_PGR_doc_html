"""Analytics - вычисление аналитических метрик для циклов.

Основные функции:
- finalize_cycle_analytics() - вычисление всех метрик цикла (включая рейс если есть)
- finalize_trip_analytics() - (legacy) вычисление метрик рейса
- Агрегация данных из cycle_state_history
- Вычисление длительностей по состояниям
- Подсчет уникальных меток
"""

from datetime import UTC
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Cycle,
    CycleAnalytics,
    CycleStateHistory,
    CycleTagHistory,
    Trip,
)


async def finalize_cycle_analytics(
    cycle_id: str,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Вычислить и сохранить аналитику цикла.

    Цикл включает все этапы работы техники:
    - moving_empty, stopped_empty (этапы ДО рейса)
    - loading, moving_loaded, stopped_loaded, unloading (этапы рейса)

    Если в цикле есть рейс, то аналитика включает данные рейса.
    Если рейса нет (ремонтный цикл), то поля рейса будут NULL.

    Args:
        cycle_id: ID цикла
        db: Database session

    Returns:
        dict с метриками или None если цикл не найден
    """
    try:
        # Проверить, не посчитана ли аналитика ранее
        existing_query = select(CycleAnalytics).where(CycleAnalytics.cycle_id == cycle_id)
        existing_result = await db.execute(existing_query)
        existing_analytics = existing_result.scalar_one_or_none()

        if existing_analytics:
            logger.info(
                "Cycle analytics already exist, skipping recalculation",
                cycle_id=cycle_id,
            )
            return existing_analytics.analytics_data

        # Получить данные цикла
        cycle_query = select(Cycle).where(Cycle.cycle_id == cycle_id)
        cycle_result = await db.execute(cycle_query)
        cycle = cycle_result.scalar_one_or_none()

        if not cycle:
            logger.error("Cycle not found for analytics", cycle_id=cycle_id)
            return None

        # Получить рейс, если есть
        trip = None
        if cycle.cycle_id:
            trip_query = select(Trip).where(Trip.cycle_id == cycle_id)
            trip_result = await db.execute(trip_query)
            trip = trip_result.scalar_one_or_none()

        # Получить историю состояний ЦИКЛА
        state_history_query = (
            select(CycleStateHistory)
            .where(
                CycleStateHistory.cycle_id == cycle_id,
            )
            .order_by(CycleStateHistory.timestamp)
        )
        state_history_result = await db.execute(state_history_query)
        state_history = list(state_history_result.scalars().all())

        # Получить историю меток ЦИКЛА
        tag_history_query = select(CycleTagHistory).where(
            CycleTagHistory.cycle_id == cycle_id,
        )
        tag_history_result = await db.execute(tag_history_query)
        tag_history = list(tag_history_result.scalars().all())

        # Вычислить метрики
        metrics = await _calculate_cycle_metrics(
            cycle=cycle,
            trip=trip,
            state_history=state_history,
            tag_history=tag_history,
        )

        # Сохранить аналитику
        analytics = CycleAnalytics(
            cycle_id=cycle_id,
            vehicle_id=cycle.vehicle_id,
            shift_id=cycle.shift_id,
            cycle_type=cycle.cycle_type,
            cycle_status=cycle.cycle_status,
            trip_type=trip.trip_type if trip else None,
            trip_status="completed" if trip and trip.end_time else None,
            from_place_id=cycle.from_place_id,
            to_place_id=cycle.to_place_id,
            cycle_started_at=cycle.cycle_started_at,
            cycle_completed_at=cycle.cycle_completed_at,
            trip_started_at=trip.start_time if trip else None,
            trip_completed_at=trip.end_time if trip else None,
            total_duration_seconds=metrics.get("total_cycle_duration_seconds"),
            moving_empty_duration_seconds=metrics.get("moving_empty_duration_seconds"),
            stopped_empty_duration_seconds=metrics.get("stopped_empty_duration_seconds"),
            loading_duration_seconds=metrics.get("loading_duration_seconds"),
            moving_loaded_duration_seconds=metrics.get("moving_loaded_duration_seconds"),
            stopped_loaded_duration_seconds=metrics.get("stopped_loaded_duration_seconds"),
            unloading_duration_seconds=metrics.get("unloading_duration_seconds"),
            state_transitions_count=metrics.get("state_transitions_count"),
            analytics_data=metrics.get("extra_metrics"),
        )

        db.add(analytics)
        await db.commit()

        logger.info(
            "Cycle analytics calculated",
            cycle_id=cycle_id,
            total_cycle_duration=metrics.get("total_cycle_duration_seconds"),
            has_trip=trip is not None,
        )

        return metrics

    except Exception as e:
        logger.error(
            "Failed to calculate cycle analytics",
            cycle_id=cycle_id,
            error=str(e),
            exc_info=True,
        )
        return None


async def finalize_trip_analytics(
    cycle_id: str,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Статистики рейса пока не реализованы в новой схеме данных.

    Возвращаем None, чтобы не прерывать рабочие процессы.
    """
    logger.warning(
        "Trip analytics is not implemented for the new data model",
        cycle_id=cycle_id,
    )
    return None


async def _calculate_trip_metrics(
    trip: Trip,
    state_history: list[CycleStateHistory],
    tag_history: list[CycleTagHistory],
) -> dict[str, Any]:
    """Вычислить все метрики рейса.

    Args:
        trip: Объект рейса
        state_history: История состояний
        tag_history: История меток

    Returns:
        dict с вычисленными метриками
    """
    metrics = {
        # Общие метрики
        "total_duration_seconds": 0,
        "loading_duration_seconds": 0,
        "unloading_duration_seconds": 0,
        "travel_loaded_duration_seconds": 0,
        "travel_empty_duration_seconds": 0,
        "stopped_duration_seconds": 0,
        # По состояниям
        "state_idle_seconds": 0,
        "state_loading_seconds": 0,
        "state_moving_loaded_seconds": 0,
        "state_unloading_seconds": 0,
        "state_moving_empty_seconds": 0,
        "state_stopped_empty_seconds": 0,
        "state_stopped_loaded_seconds": 0,
        # Метки
        "unique_tags_count": 0,
        # Дополнительные (если есть данные)
        "distance_km": None,
        "average_speed_kmh": None,
        "max_speed_kmh": None,
        "fuel_consumed_liters": None,
        "weight_loaded_tons": None,
        "cargo_type": None,
    }

    # 1. Общая длительность рейса
    if trip.start_time and trip.end_time:
        try:
            total_duration = (trip.end_time - trip.start_time).total_seconds()
        except TypeError:
            # Если один из timestamp-ов без timezone, добавляем UTC
            start_time = trip.start_time if trip.start_time.tzinfo else trip.start_time.replace(tzinfo=UTC)
            end_time = trip.end_time if trip.end_time.tzinfo else trip.end_time.replace(tzinfo=UTC)
            total_duration = (end_time - start_time).total_seconds()
        metrics["total_duration_seconds"] = int(total_duration)

    # 2. Вычисление длительностей по состояниям
    state_durations = _calculate_state_durations(state_history)

    # Маппинг состояний на категории
    metrics["state_idle_seconds"] = state_durations.get("idle", 0)
    metrics["state_loading_seconds"] = state_durations.get("loading", 0)
    metrics["state_moving_loaded_seconds"] = state_durations.get("moving_loaded", 0)
    metrics["state_unloading_seconds"] = state_durations.get("unloading", 0)
    metrics["state_moving_empty_seconds"] = state_durations.get("moving_empty", 0)
    metrics["state_stopped_empty_seconds"] = state_durations.get("stopped_empty", 0)
    metrics["state_stopped_loaded_seconds"] = state_durations.get("stopped_loaded", 0)

    # Количество переходов состояний
    if state_history:
        metrics["state_transitions_count"] = len(state_history)

    # Агрегированные метрики
    # Длительности состояний берём напрямую из state_* без смешивания
    metrics["loading_duration_seconds"] = metrics["state_loading_seconds"]
    metrics["unloading_duration_seconds"] = metrics["state_unloading_seconds"]
    metrics["travel_loaded_duration_seconds"] = metrics["state_moving_loaded_seconds"]
    metrics["travel_empty_duration_seconds"] = metrics["state_moving_empty_seconds"]
    metrics["stopped_duration_seconds"] = int(metrics["state_stopped_empty_seconds"] or 0) + int(
        metrics["state_stopped_loaded_seconds"] or 0,
    )

    # Дополнительные поля для модели TripAnalytics (дублируем из state_* для удобства)
    metrics["moving_empty_duration_seconds"] = metrics["state_moving_empty_seconds"]
    metrics["stopped_empty_duration_seconds"] = metrics["state_stopped_empty_seconds"]
    metrics["moving_loaded_duration_seconds"] = metrics["state_moving_loaded_seconds"]
    metrics["stopped_loaded_duration_seconds"] = metrics["state_stopped_loaded_seconds"]

    # 3. Количество уникальных меток
    if tag_history:
        unique_points = set(tag.tag_id for tag in tag_history)
        metrics["unique_tags_count"] = len(unique_points)

    return metrics


def _calculate_state_durations(state_history: list[CycleStateHistory]) -> dict[str, int]:
    """Вычислить длительности каждого состояния.

    Args:
        state_history: Список записей TripStateHistory

    Returns:
        dict: {state: duration_seconds}
    """
    durations: dict[str, int] = {}

    if not state_history:
        return durations

    # Сортировать по времени
    sorted_history = sorted(state_history, key=lambda x: x.timestamp)

    for i in range(len(sorted_history)):
        current = sorted_history[i]
        state = current.state

        # Вычислить длительность состояния
        if i < len(sorted_history) - 1:
            # Длительность = следующее состояние - текущее
            next_state = sorted_history[i + 1]
            try:
                duration = (next_state.timestamp - current.timestamp).total_seconds()
            except TypeError:
                # Если один из timestamp-ов без timezone, добавляем UTC
                current_ts = current.timestamp if current.timestamp.tzinfo else current.timestamp.replace(tzinfo=UTC)
                next_ts = (
                    next_state.timestamp if next_state.timestamp.tzinfo else next_state.timestamp.replace(tzinfo=UTC)
                )
                duration = (next_ts - current_ts).total_seconds()
        else:
            # Последнее состояние - длительность до текущего момента (или 0)
            duration = 0

        # Суммировать длительности для каждого состояния
        if state not in durations:
            durations[state] = 0
        durations[state] += int(duration)

    return durations


async def _calculate_cycle_metrics(
    cycle: Cycle,
    trip: Trip | None,
    state_history: list[CycleStateHistory],
    tag_history: list[CycleTagHistory],
) -> dict[str, Any]:
    """Вычислить все метрики цикла.

    Включает все этапы цикла, независимо от наличия рейса.

    Args:
        cycle: Объект цикла
        trip: Объект рейса (может быть None для ремонтного цикла)
        state_history: История состояний цикла
        tag_history: История меток цикла

    Returns:
        dict с вычисленными метриками
    """
    # Вычислить длительности по состояниям
    state_durations = _calculate_state_durations(state_history)

    # Маппинг состояний
    moving_empty_duration = state_durations.get("moving_empty", 0)
    stopped_empty_duration = state_durations.get("stopped_empty", 0)
    loading_duration = state_durations.get("loading", 0)
    moving_loaded_duration = state_durations.get("moving_loaded", 0)
    stopped_loaded_duration = state_durations.get("stopped_loaded", 0)
    unloading_duration = state_durations.get("unloading", 0)

    # Общая длительность цикла
    total_cycle_duration: float = 0
    if cycle.cycle_started_at and cycle.cycle_completed_at:
        try:
            total_cycle_duration = (cycle.cycle_completed_at - cycle.cycle_started_at).total_seconds()
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
            total_cycle_duration = (end_time - start_time).total_seconds()

    metrics: dict[str, Any] = {
        # Метрики цикла
        "total_cycle_duration_seconds": int(total_cycle_duration),
        "moving_empty_duration_seconds": moving_empty_duration,
        "stopped_empty_duration_seconds": stopped_empty_duration,
        "loading_duration_seconds": loading_duration,
        "moving_loaded_duration_seconds": moving_loaded_duration,
        "stopped_loaded_duration_seconds": stopped_loaded_duration,
        "unloading_duration_seconds": unloading_duration,
        # Количество переходов состояний
        "state_transitions_count": len(state_history) if state_history else 0,
        # Количество уникальных меток
        "unique_tags_count": len(set(tag.tag_id for tag in tag_history)) if tag_history else 0,
    }

    # Дополнительные метрики, если есть рейс
    extra_metrics: dict[str, Any] = {}
    if trip:
        # Длительность рейса (только moving_loaded + stopped_loaded + unloading)
        trip_duration = moving_loaded_duration + stopped_loaded_duration + unloading_duration
        extra_metrics["trip_duration_seconds"] = trip_duration

        # Процент времени с грузом от общего времени цикла
        if total_cycle_duration > 0:
            extra_metrics["loaded_time_percentage"] = round(
                (trip_duration / total_cycle_duration) * 100,
                2,
            )
            extra_metrics["empty_time_percentage"] = round(
                ((moving_empty_duration + stopped_empty_duration) / total_cycle_duration) * 100,
                2,
            )

    metrics["extra_metrics"] = extra_metrics if extra_metrics else None

    return metrics
