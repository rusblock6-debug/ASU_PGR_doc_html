"""Сервис для расчета обобщенных статусов смен (full_shift_state_history).

Периодически (раз в минуту) рассчитывает агрегированный статус для каждой смены
на основе данных cycle_state_history.

Правила расчета:
- 'no_data': нет записей в cycle_state_history или только статусы 'no_data'
- Для остальных случаев:
  - Рассчитываются длительности:
    * work_duration: сумма длительностей статусов с is_work_status=true (в секундах)
    * idle_duration: сумма длительностей статусов с is_work_status=false (в секундах)
  - Если idle_duration > 50% от общей длительности смены -> 'idle'
  - Иначе -> 'work'

Дополнительно:
- Для текущей смены всегда ставится is_processed=false (пересчитывается каждый раз)
- Если в начале текущей смены нет записи cycle_state_history, копируется
  последняя запись до начала смены (продление статуса с предыдущей смены)
- Длительности рассчитываются на основе времени между последовательными записями
- При публикации события history_changed уведомляется фронтенд через SSE /api/events/stream/all
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models import CycleStateHistory, FullShiftStateHistory
from app.database.session import AsyncSessionLocal
from app.services.enterprise_client import enterprise_client
from app.services.state_history_service import _publish_history_changed_event


class FullShiftStateService:
    """Сервис для расчета и записи обобщенных статусов смен."""

    def __init__(self) -> None:
        self.tz = ZoneInfo(settings.timezone)
        self._status_work_flags: dict[str, bool] | None = None  # Кеш system_name -> is_work_status

    async def _get_status_work_flags(self) -> dict[str, bool]:
        """Получить маппинг system_name -> is_work_status из enterprise-service.

        Кешируется на время жизни объекта.

        Returns:
            Словарь {system_name: is_work_status}
        """
        if self._status_work_flags is None:
            try:
                statuses = await enterprise_client.get_all_statuses()
                self._status_work_flags = {
                    str(s["system_name"]): bool(s.get("is_work_status", False))
                    for s in statuses
                    if s.get("system_name")
                }
                logger.info(
                    "Loaded status work flags",
                    count=len(self._status_work_flags),
                )
            except Exception as e:
                logger.error("Error loading status work flags", error=str(e))
                self._status_work_flags = {}

        return self._status_work_flags

    async def process_all_shifts(self) -> dict[str, int]:
        """Обработать все смены за последнюю неделю для всех активных vehicles.

        Returns:
            Статистика обработки: {"processed": N, "created": M, "updated": K, "errors": E, "extended": X}
        """
        stats = {"processed": 0, "created": 0, "updated": 0, "errors": 0, "extended": 0}

        try:
            # 1. Получить список активных vehicles
            vehicles = await enterprise_client.get_active_vehicles()
            if not vehicles:
                logger.warning("No active vehicles found in enterprise-service")
                return stats

            vehicle_ids = [v["id"] for v in vehicles]
            logger.info(f"Processing {len(vehicle_ids)} active vehicles")

            # 2. Получить конфигурацию смен из work_regimes (берем первый активный)
            work_regimes = await enterprise_client.get_active_work_regimes()
            if not work_regimes:
                logger.warning("No active work regimes found in enterprise-service")
                return stats

            # Берем первый активный режим
            work_regime = work_regimes[0]
            shifts_definition = work_regime.get("shifts_definition", [])
            num_shifts = len(shifts_definition)

            if num_shifts == 0:
                logger.warning("Work regime has no shifts defined", work_regime_id=work_regime["id"])
                return stats

            logger.info(
                "Using work regime",
                work_regime_id=work_regime["id"],
                work_regime_name=work_regime.get("name"),
                num_shifts=num_shifts,
            )

            # 3. Определить текущую смену через enterprise-service
            current_shift_info = await enterprise_client.get_current_shift_info(
                work_regime_id=work_regime["id"],
            )

            logger.info(
                "Response from enterprise-service get_current_shift_info",
                response=current_shift_info,
                work_regime_id=work_regime["id"],
            )

            if not current_shift_info:
                logger.warning("Could not determine current shift from enterprise-service")
                # Fallback: берем первую смену сегодня
                current_shift_date = date.today()
                current_shift_num = 1
            else:
                current_shift_date = date.fromisoformat(current_shift_info["shift_date"])
                current_shift_num = current_shift_info["shift_num"]

            logger.info(
                "Current shift identified",
                current_shift_date=current_shift_date.isoformat(),
                current_shift_num=current_shift_num,
            )

            # 4. Определить диапазон дат
            # Начало: неделя назад от сегодня
            # Конец: current_shift_date (может быть "завтра" для ночных смен)
            today = date.today()
            start_date = today - timedelta(days=7)
            end_date = current_shift_date  # Включаем дату текущей смены

            # 5. Для каждого vehicle и каждой смены
            async with AsyncSessionLocal() as db:
                for vehicle_id in vehicle_ids:
                    existing_shift_records = await self._load_existing_shift_records(
                        db=db,
                        vehicle_id=vehicle_id,
                        start_date=start_date,
                        end_date=end_date,
                    )

                    # 5.1. Проверить и продлить статус для текущей смены
                    try:
                        extended = await self._extend_status_to_current_shift(
                            db=db,
                            vehicle_id=vehicle_id,
                            current_shift_date=current_shift_date,
                            current_shift_num=current_shift_num,
                            work_regime_id=work_regime["id"],
                        )
                        if extended:
                            stats["extended"] += 1
                    except Exception as e:
                        logger.error(
                            "Error extending status to current shift",
                            vehicle_id=vehicle_id,
                            error=str(e),
                        )

                    # 5.2. Обработать все смены до текущей включительно
                    current_date = start_date
                    while current_date <= end_date:
                        # Для даты current_shift_date обрабатываем только смены
                        # до current_shift_num включительно (будущие смены не трогаем)
                        if current_date == current_shift_date:
                            max_shift = current_shift_num
                        else:
                            max_shift = num_shifts

                        for shift_num in range(1, max_shift + 1):
                            try:
                                # Определяем, является ли это текущей сменой
                                is_current_shift = current_date == current_shift_date and shift_num == current_shift_num

                                result = await self._process_single_shift(
                                    db=db,
                                    vehicle_id=vehicle_id,
                                    shift_date=current_date,
                                    shift_num=shift_num,
                                    work_regime_id=work_regime["id"],
                                    is_current_shift=is_current_shift,
                                    existing_record=existing_shift_records.get(
                                        (current_date.isoformat(), shift_num),
                                    ),
                                    existing_records_cache=existing_shift_records,
                                )
                                stats["processed"] += 1
                                if result == "created":
                                    stats["created"] += 1
                                elif result == "updated":
                                    stats["updated"] += 1
                            except Exception as e:
                                stats["errors"] += 1
                                logger.error(
                                    "Error processing shift",
                                    vehicle_id=vehicle_id,
                                    shift_date=current_date.isoformat(),
                                    shift_num=shift_num,
                                    error=str(e),
                                )

                        current_date += timedelta(days=1)

                # Коммитим все изменения
                await db.commit()

        except Exception as e:
            logger.error("Error in process_all_shifts", error=str(e), exc_info=True)
            stats["errors"] += 1

        logger.info(
            "Finished processing shifts",
            processed=stats["processed"],
            created=stats["created"],
            updated=stats["updated"],
            extended=stats["extended"],
            errors=stats["errors"],
        )

        return stats

    async def _load_existing_shift_records(
        self,
        db: AsyncSession,
        vehicle_id: int,
        start_date: date,
        end_date: date,
    ) -> dict[tuple[str, int], FullShiftStateHistory]:
        """Загрузить существующие агрегированные записи смен для vehicle одним запросом."""
        result = await db.execute(
            select(FullShiftStateHistory).where(
                and_(
                    FullShiftStateHistory.vehicle_id == vehicle_id,
                    FullShiftStateHistory.shift_date >= start_date.isoformat(),
                    FullShiftStateHistory.shift_date <= end_date.isoformat(),
                ),
            ),
        )

        return {(record.shift_date, record.shift_num): record for record in result.scalars().all()}

    async def _extend_status_to_current_shift(
        self,
        db: AsyncSession,
        vehicle_id: int,
        current_shift_date: date,
        current_shift_num: int,
        work_regime_id: int,
    ) -> bool:
        """Продлить статус с предыдущей смены на начало текущей смены.

        Если в начале текущей смены нет записи в cycle_state_history,
        копирует последнюю запись до начала смены.

        Args:
            db: Database session
            vehicle_id: ID транспортного средства
            current_shift_date: Дата текущей смены
            current_shift_num: Номер текущей смены
            work_regime_id: ID режима работы

        Returns:
            True если статус был продлен, False иначе
        """
        # 1. Получить временной диапазон текущей смены
        shift_time_range = await enterprise_client.get_shift_time_range(
            shift_date=current_shift_date,
            shift_number=current_shift_num,
            work_regime_id=work_regime_id,
        )

        if not shift_time_range:
            return False

        shift_start_time = datetime.fromisoformat(shift_time_range["start_time"])

        # 2. Проверить, есть ли запись в начале смены (в пределах 1 минуты от начала)
        time_window_start = shift_start_time
        time_window_end = shift_start_time + timedelta(minutes=1)

        existing_at_start = await db.execute(
            select(CycleStateHistory)
            .where(
                and_(
                    CycleStateHistory.vehicle_id == vehicle_id,
                    CycleStateHistory.timestamp >= time_window_start,
                    CycleStateHistory.timestamp < time_window_end,
                ),
            )
            .limit(1),
        )

        if existing_at_start.scalar_one_or_none():
            # Запись уже есть - ничего не делаем
            return False

        # 3. Найти последнюю запись до начала смены
        last_record_result = await db.execute(
            select(CycleStateHistory)
            .where(
                and_(
                    CycleStateHistory.vehicle_id == vehicle_id,
                    CycleStateHistory.timestamp < shift_start_time,
                ),
            )
            .order_by(desc(CycleStateHistory.timestamp))
            .limit(1),
        )
        last_record = last_record_result.scalar_one_or_none()

        if not last_record:
            # Нет предыдущих записей - ничего не копируем
            logger.debug(
                "No previous records to extend",
                vehicle_id=vehicle_id,
                shift_start_time=shift_start_time.isoformat(),
            )
            return False

        # 4. Копировать запись на начало текущей смены
        new_record = CycleStateHistory(
            id=str(uuid.uuid4())[:32],
            timestamp=shift_start_time,
            vehicle_id=vehicle_id,
            cycle_id=last_record.cycle_id,
            state=last_record.state,
            state_data=last_record.state_data.copy() if last_record.state_data else {},
            place_id=last_record.place_id,
            source="system",
            task_id=last_record.task_id,
            trigger_type="shift_extension",
            trigger_data={"extended_from": last_record.id},
        )
        db.add(new_record)

        logger.info(
            "Extended status to current shift start",
            vehicle_id=vehicle_id,
            shift_start_time=shift_start_time.isoformat(),
            extended_from_id=last_record.id,
            state=last_record.state,
        )

        return True

    async def _process_single_shift(
        self,
        db: AsyncSession,
        vehicle_id: int,
        shift_date: date,
        shift_num: int,
        work_regime_id: int,
        is_current_shift: bool = False,
        existing_record: FullShiftStateHistory | None = None,
        existing_records_cache: dict[tuple[str, int], FullShiftStateHistory] | None = None,
    ) -> str | None:
        """Обработать одну смену для vehicle.

        Args:
            db: Database session
            vehicle_id: ID транспортного средства
            shift_date: Дата смены
            shift_num: Номер смены
            work_regime_id: ID режима работы
            is_current_shift: True если это текущая смена (всегда пересчитывается)
            existing_record: Уже загруженная запись full_shift_state_history для смены, если есть
            existing_records_cache: Кеш записей смен vehicle для обновления после создания новой записи

        Returns:
            "created" если создана новая запись,
            "updated" если обновлена существующая,
            None если запись актуальна и не требует обновления
        """
        shift_date_str = shift_date.isoformat()

        # Если запись существует и обработана И это не текущая смена - пропускаем
        # Для текущей смены всегда пересчитываем
        if existing_record and existing_record.is_processed and not is_current_shift:
            return None

        # 2. Получить временной диапазон смены
        shift_time_range = await enterprise_client.get_shift_time_range(
            shift_date=shift_date,
            shift_number=shift_num,
            work_regime_id=work_regime_id,
        )

        if not shift_time_range:
            logger.warning(
                "Could not get shift time range",
                vehicle_id=vehicle_id,
                shift_date=shift_date.isoformat(),
                shift_num=shift_num,
            )
            return None

        start_time = datetime.fromisoformat(shift_time_range["start_time"])
        end_time = datetime.fromisoformat(shift_time_range["end_time"])

        # 3. Получить записи cycle_state_history для этой смены и vehicle
        history_result = await db.execute(
            select(CycleStateHistory).where(
                and_(
                    CycleStateHistory.vehicle_id == vehicle_id,
                    CycleStateHistory.timestamp >= start_time,
                    CycleStateHistory.timestamp < end_time,
                ),
            ),
        )
        history_records = list(history_result.scalars().all())

        # 4. Получить маппинг is_work_status
        status_work_flags = await self._get_status_work_flags()

        # 5. Рассчитать статус и длительности
        state, idle_duration, work_duration = self._calculate_shift_state(
            records=history_records,
            start_time=start_time,
            end_time=end_time,
            status_work_flags=status_work_flags,
            is_current_shift=is_current_shift,
        )

        # 6. Определить is_processed:
        # - Для текущей смены всегда False (пересчитывается каждый раз)
        # - Для прошлых смен - True
        is_processed = not is_current_shift

        # 7. Создать или обновить запись
        if existing_record:
            existing_record.state = state
            existing_record.timestamp = start_time
            existing_record.is_processed = is_processed
            existing_record.idle_duration = idle_duration
            existing_record.work_duration = work_duration
            result = "updated"
        else:
            new_record = FullShiftStateHistory(
                id=str(uuid.uuid4())[:32],
                vehicle_id=vehicle_id,
                shift_num=shift_num,
                shift_date=shift_date_str,
                state=state,
                timestamp=start_time,
                source="system",
                is_processed=is_processed,
                idle_duration=idle_duration,
                work_duration=work_duration,
            )
            db.add(new_record)
            if existing_records_cache is not None:
                existing_records_cache[(shift_date_str, shift_num)] = new_record
            result = "created"

        # 7. Публикуем событие для фронта (SSE /api/events/stream/all)
        await _publish_history_changed_event(
            vehicle_id=vehicle_id,
            shift_date=shift_date_str,
            shift_num=shift_num,
        )

        return result

    def _calculate_shift_state(
        self,
        records: list[CycleStateHistory],
        start_time: datetime,
        end_time: datetime,
        status_work_flags: dict[str, bool],
        is_current_shift: bool = False,
    ) -> tuple[str, int | None, int | None]:
        """Рассчитать обобщенный статус смены и длительности.

        Правила:
        - Если нет записей или только записи с state='no_data' -> ('no_data', None, None)
        - Иначе рассчитываем длительности:
          - work_duration: сумма длительностей статусов с is_work_status=true
          - idle_duration: сумма длительностей статусов с is_work_status=false
        - Для текущей смены последний статус тянется до текущего момента (now), а не до конца смены
        - Статус смены:
          - Если idle_duration > 50% от общей длительности -> 'idle'
          - Иначе -> 'work'

        Args:
            records: Список записей cycle_state_history для смены
            start_time: Время начала смены
            end_time: Время конца смены
            status_work_flags: Словарь system_name -> is_work_status
            is_current_shift: True для текущей смены (последний статус до now, не до end_time)

        Returns:
            Кортеж (state, idle_duration, work_duration):
            - state: 'no_data', 'work' или 'idle'
            - idle_duration: длительность простоя в секундах (или None)
            - work_duration: длительность работы в секундах (или None)
        """
        if not records:
            return "no_data", None, None

        # Фильтруем записи - проверяем только не-no_data
        non_no_data_records = [r for r in records if r.state != "no_data"]

        if not non_no_data_records:
            # Все записи - no_data
            return "no_data", None, None

        # Сортируем записи по timestamp
        sorted_records = sorted(non_no_data_records, key=lambda r: r.timestamp)

        # Рассчитываем длительности
        work_duration_seconds: float = 0
        idle_duration_seconds: float = 0

        # Для текущей смены последний статус тянется до now, для прошлых — до end_time
        now = datetime.now(UTC)
        end_utc = end_time if end_time.tzinfo else end_time.replace(tzinfo=UTC)
        effective_end = min(end_utc, now) if is_current_shift else end_utc

        for i, record in enumerate(sorted_records):
            # Определяем is_work_status для текущего статуса
            is_work = status_work_flags.get(record.state, False)

            # Определяем длительность до следующего события или до конца смены
            if i < len(sorted_records) - 1:
                # Длительность до следующей записи
                next_timestamp = sorted_records[i + 1].timestamp
                duration = (next_timestamp - record.timestamp).total_seconds()
            else:
                # Последняя запись: для текущей смены — до now, для прошлой — до end_time
                duration = (effective_end - record.timestamp).total_seconds()

            # Если длительность отрицательная (запись вне смены) - пропускаем
            if duration < 0:
                continue

            # Добавляем к соответствующему счётчику
            if is_work:
                work_duration_seconds += duration
            else:
                idle_duration_seconds += duration

        # Округляем до целых секунд
        idle_duration = int(round(idle_duration_seconds))
        work_duration = int(round(work_duration_seconds))

        # Определяем статус на основе процента idle
        total_duration = idle_duration + work_duration
        if total_duration == 0:
            # Нет длительностей - считаем как no_data
            return "no_data", None, None

        idle_percent = (idle_duration / total_duration) * 100

        if idle_percent > 50:
            state = "idle"
        else:
            state = "work"

        return state, idle_duration, work_duration

    async def mark_shift_not_actual(
        self,
        vehicle_id: int,
        shift_date: date,
        shift_num: int,
    ) -> bool:
        """Пометить запись смены как неактуальную для пересчета.

        Используется когда данные cycle_state_history изменились и нужен пересчет.

        Args:
            vehicle_id: ID транспортного средства
            shift_date: Дата смены
            shift_num: Номер смены

        Returns:
            True если запись найдена и обновлена, False иначе
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(FullShiftStateHistory).where(
                    and_(
                        FullShiftStateHistory.vehicle_id == vehicle_id,
                        FullShiftStateHistory.shift_date == shift_date.isoformat(),
                        FullShiftStateHistory.shift_num == shift_num,
                    ),
                ),
            )
            record = result.scalar_one_or_none()

            if record:
                record.is_processed = False
                await db.commit()
                logger.info(
                    "Marked shift as not actual",
                    vehicle_id=vehicle_id,
                    shift_date=shift_date.isoformat(),
                    shift_num=shift_num,
                )
                return True

            return False

    async def invalidate_shift_by_timestamp(
        self,
        vehicle_id: int,
        timestamp: datetime,
        work_regime_id: int | None = None,
    ) -> bool:
        """Пометить смену как неактуальную по vehicle_id и timestamp.

        Определяет смену по timestamp через enterprise-service и помечает её is_processed=false.

        Args:
            vehicle_id: ID транспортного средства
            timestamp: Время события (для определения смены)
            work_regime_id: ID режима работы (опционально)

        Returns:
            True если смена найдена и помечена, False иначе
        """
        try:
            # Получить информацию о смене по timestamp
            shift_info = await enterprise_client.get_shift_info_by_timestamp(
                timestamp=timestamp,
                work_regime_id=work_regime_id,
            )

            if not shift_info:
                logger.warning(
                    "Could not determine shift for timestamp",
                    vehicle_id=vehicle_id,
                    timestamp=timestamp.isoformat(),
                )
                return False

            shift_date = date.fromisoformat(shift_info["shift_date"])
            shift_num = shift_info["shift_num"]

            return await self.mark_shift_not_actual(
                vehicle_id=vehicle_id,
                shift_date=shift_date,
                shift_num=shift_num,
            )
        except Exception as e:
            logger.error(
                "Error invalidating shift by timestamp",
                vehicle_id=vehicle_id,
                timestamp=timestamp.isoformat(),
                error=str(e),
            )
            return False


# Глобальный экземпляр сервиса
full_shift_state_service = FullShiftStateService()
