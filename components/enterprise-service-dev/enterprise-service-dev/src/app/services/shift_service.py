"""ShiftService - динамический расчет смен на основе WorkRegime."""

from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WorkRegime
from app.schemas.work_regimes import ShiftDefinition


class ShiftService:
    """Сервис для динамического вычисления смен.

    Смены НЕ хранятся в БД, а вычисляются на лету из WorkRegime.
    """

    @staticmethod
    async def get_shift_info_by_timestamp(
        timestamp: datetime,
        work_regime_id: int | None = None,
        timezone: str = "Europe/Moscow",
        db: AsyncSession | None = None,
    ) -> dict[str, Any] | None:
        """Определить shift_date и shift_num для заданного timestamp.

        Args:
            timestamp: Время для определения смены
            work_regime_id: ID режима работы (если None - берется первый активный)
            timezone: Временная зона
            db: Database session

        Returns:
            Словарь с shift_date и shift_num или None если не найдено
        """
        if not db:
            return None

        # Если work_regime_id не передан, берем первый активный
        if not work_regime_id:
            result = await db.execute(
                select(WorkRegime).where(WorkRegime.is_active).limit(1),
            )
            regime = result.scalar_one_or_none()
        else:
            result = await db.execute(
                select(WorkRegime).where(WorkRegime.id == work_regime_id),
            )
            regime = result.scalar_one_or_none()

        if not regime or not regime.is_active:
            return None

        tz = ZoneInfo(timezone)
        # Предполагаем, что timestamp приходит как naive datetime в UTC
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC).astimezone(tz)
        else:
            timestamp = timestamp.astimezone(tz)

        raw_shifts = cast(list[dict[str, Any]], regime.shifts_definition)
        shifts_def = [ShiftDefinition(**shift_dict) for shift_dict in raw_shifts]

        target_date = timestamp.date()

        for shift_def in shifts_def:
            begin_seconds = shift_def.start_time_offset
            end_seconds = shift_def.end_time_offset

            # Обрабатываем отрицательные значения (смена начинается в предыдущий день)
            if begin_seconds < 0:
                shift_start_date = target_date - timedelta(days=1)
                begin_seconds_adjusted = begin_seconds + 86400
            else:
                shift_start_date = target_date
                begin_seconds_adjusted = begin_seconds

            # Время начала смены
            begin_hours = begin_seconds_adjusted // 3600
            begin_minutes = (begin_seconds_adjusted % 3600) // 60
            begin_secs = begin_seconds_adjusted % 60
            shift_start = datetime.combine(shift_start_date, datetime.min.time()).replace(
                hour=begin_hours,
                minute=begin_minutes,
                second=begin_secs,
                tzinfo=tz,
            )

            # Время конца смены
            end_hours = end_seconds // 3600
            end_minutes = (end_seconds % 3600) // 60
            end_secs = end_seconds % 60

            if end_seconds >= begin_seconds:
                # Смена в пределах одного дня (или начинается накануне)
                shift_end = datetime.combine(target_date, datetime.min.time()).replace(
                    hour=end_hours,
                    minute=end_minutes,
                    second=end_secs,
                    tzinfo=tz,
                )
            else:
                # Смена пересекает полночь (конец на следующий день от target_date)
                next_date = target_date + timedelta(days=1)
                shift_end = datetime.combine(next_date, datetime.min.time()).replace(
                    hour=end_hours,
                    minute=end_minutes,
                    second=end_secs,
                    tzinfo=tz,
                )

            # Проверяем, попадает ли timestamp в интервал смены
            # Начало включительно, конец исключительно [start, end)
            if shift_start <= timestamp < shift_end:
                return {
                    "shift_date": target_date.isoformat(),
                    "shift_num": shift_def.shift_num,
                }

        # Если не нашли на текущую дату, проверяем смены СЛЕДУЮЩЕГО дня,
        # которые начинаются накануне (т.е. сегодня вечером)
        # Пример: 16.01 22:00 - это смена 1 даты 17.01 (которая идет с 20:00 16.01 до 08:00 17.01)
        next_date = target_date + timedelta(days=1)
        for shift_def in shifts_def:
            begin_seconds = shift_def.start_time_offset
            end_seconds = shift_def.end_time_offset

            # Проверяем смены с отрицательным offset (начинаются накануне)
            if begin_seconds < 0:
                # Для смены даты next_date: начало будет target_date (сегодня)
                begin_seconds_adjusted = begin_seconds + 86400

                begin_hours = begin_seconds_adjusted // 3600
                begin_minutes = (begin_seconds_adjusted % 3600) // 60
                begin_secs = begin_seconds_adjusted % 60
                shift_start = datetime.combine(target_date, datetime.min.time()).replace(
                    hour=begin_hours,
                    minute=begin_minutes,
                    second=begin_secs,
                    tzinfo=tz,
                )

                end_hours = end_seconds // 3600
                end_minutes = (end_seconds % 3600) // 60
                end_secs = end_seconds % 60
                shift_end = datetime.combine(next_date, datetime.min.time()).replace(
                    hour=end_hours,
                    minute=end_minutes,
                    second=end_secs,
                    tzinfo=tz,
                )

                # Начало включительно, конец исключительно [start, end)
                if shift_start <= timestamp < shift_end:
                    return {
                        "shift_date": next_date.isoformat(),
                        "shift_num": shift_def.shift_num,
                    }

        return None

    @staticmethod
    async def get_current_shift(
        work_regime_id: str | None = None,
        timestamp: datetime | None = None,
        timezone: str = "Europe/Moscow",
        db: AsyncSession | None = None,
    ) -> dict[str, Any] | None:
        """Получить текущую смену для режима работы.

        Args:
            work_regime_id: ID режима работы
            timestamp: Время для проверки (если None - сейчас)
            timezone: Временная зона (default: Europe/Moscow)
            db: Database session

        Returns:
            Словарь с информацией о текущей смене или None если режим неактивен
        """
        if not work_regime_id or not db:
            return None

        # Получить режим работы
        result = await db.execute(
            select(WorkRegime).where(WorkRegime.id == work_regime_id),
        )
        regime = result.scalar_one_or_none()

        if not regime or not regime.is_active:
            return None

        # Получить текущее время в нужной зоне
        if timestamp is None:
            tz = ZoneInfo(timezone)
            timestamp = datetime.now(tz)

        # Получить секунды от начала дня
        seconds_from_midnight = timestamp.hour * 3600 + timestamp.minute * 60 + timestamp.second

        # Найти смену
        shifts_def_current = [
            ShiftDefinition(**d) for d in cast(list[dict[str, Any]], regime.shifts_definition)
        ]
        for shift_def in shifts_def_current:
            begin_seconds = shift_def.start_time_offset
            end_seconds = shift_def.end_time_offset

            # Обработка смен, пересекающих полночь
            if begin_seconds >= end_seconds:  # Смена пересекает полночь (например, 20:00 - 08:00)
                if seconds_from_midnight >= begin_seconds or seconds_from_midnight < end_seconds:
                    return {
                        "shift_number": shift_def.shift_num,
                        "name": f"Смена {shift_def.shift_num}",
                        "begin_offset_seconds": begin_seconds,
                        "end_offset_seconds": end_seconds,
                        "current_time_offset": seconds_from_midnight,
                        "timestamp": timestamp.isoformat(),
                    }
            else:  # Обычная смена в пределах одного дня
                if begin_seconds <= seconds_from_midnight < end_seconds:
                    return {
                        "shift_number": shift_def.shift_num,
                        "name": f"Смена {shift_def.shift_num}",
                        "begin_offset_seconds": begin_seconds,
                        "end_offset_seconds": end_seconds,
                        "current_time_offset": seconds_from_midnight,
                        "timestamp": timestamp.isoformat(),
                    }

        logger.warning(
            "No matching shift found",
            work_regime_id=work_regime_id,
            seconds_from_midnight=seconds_from_midnight,
        )
        return None

    @staticmethod
    async def get_shifts_for_date(
        target_date: date,
        work_regime_id: str | None = None,
        timezone: str = "Europe/Moscow",
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Получить все смены для конкретной даты.

        Args:
            target_date: Дата для которой нужны смены
            work_regime_id: ID режима работы
            timezone: Временная зона
            db: Database session

        Returns:
            Список смен на дату
        """
        if not work_regime_id or not db:
            return []

        # Получить режим работы
        result = await db.execute(
            select(WorkRegime).where(WorkRegime.id == work_regime_id),
        )
        regime = result.scalar_one_or_none()

        if not regime or not regime.is_active:
            return []

        tz = ZoneInfo(timezone)
        shifts = []
        shifts_def = [
            ShiftDefinition(**shift_dict)
            for shift_dict in cast(list[dict[str, Any]], regime.shifts_definition)
        ]

        for shift_def in shifts_def:
            begin_seconds = shift_def.start_time_offset
            end_seconds = shift_def.end_time_offset

            # Вычислить время начала смены (работаем с секундами)
            begin_hours = begin_seconds // 3600
            begin_minutes = (begin_seconds % 3600) // 60
            begin_secs = begin_seconds % 60
            shift_start = datetime.combine(target_date, datetime.min.time()).replace(
                hour=begin_hours,
                minute=begin_minutes,
                second=begin_secs,
                tzinfo=tz,
            )

            # Вычислить время конца смены
            end_hours = end_seconds // 3600
            end_minutes = (end_seconds % 3600) // 60
            end_secs = end_seconds % 60

            if end_seconds >= begin_seconds:
                # Смена в пределах одного дня
                shift_end = datetime.combine(target_date, datetime.min.time()).replace(
                    hour=end_hours,
                    minute=end_minutes,
                    second=end_secs,
                    tzinfo=tz,
                )
            else:
                # Смена пересекает полночь (конец на следующий день)
                next_date = target_date + timedelta(days=1)
                shift_end = datetime.combine(next_date, datetime.min.time()).replace(
                    hour=end_hours,
                    minute=end_minutes,
                    second=end_secs,
                    tzinfo=tz,
                )

            shifts.append(
                {
                    "shift_number": shift_def.shift_num,
                    "name": f"Смена {shift_def.shift_num}",
                    "begin_offset_seconds": begin_seconds,
                    "end_offset_seconds": end_seconds,
                    "start_time": shift_start.isoformat(),
                    "end_time": shift_end.isoformat(),
                    "date": target_date.isoformat(),
                    "crosses_midnight": end_seconds < begin_seconds,
                },
            )

        logger.info(
            "Retrieved shifts for date",
            work_regime_id=work_regime_id,
            target_date=target_date.isoformat(),
            shifts_count=len(shifts),
        )

        return shifts

    @staticmethod
    async def get_shift_time_range(
        shift_date: date,
        shift_number: int,
        work_regime_id: int | None = None,
        timezone: str = "Europe/Moscow",
        db: AsyncSession | None = None,
    ) -> dict[str, datetime] | None:
        """Получить временной диапазон для конкретной смены на конкретную дату.

        Args:
            shift_date: Дата смены
            shift_number: Номер смены (1, 2, 3, etc.)
            work_regime_id: ID режима работы (если None - берем первую активную запись)
            timezone: Временная зона
            db: Database session

        Returns:
            Словарь с 'start_time' и 'end_time' или None если смена не найдена
        """
        if not db:
            return None

        # Если work_regime_id не указан, берем первую активную запись
        if work_regime_id is None:
            result = await db.execute(
                select(WorkRegime).where(WorkRegime.is_active).limit(1),
            )
            regime = result.scalar_one_or_none()
        else:
            result = await db.execute(
                select(WorkRegime).where(WorkRegime.id == work_regime_id),
            )
            regime = result.scalar_one_or_none()

        if not regime or not regime.is_active:
            logger.warning(
                "No active work regime found",
                work_regime_id=work_regime_id,
                shift_date=shift_date.isoformat(),
                shift_number=shift_number,
            )
            return None

        tz = ZoneInfo(timezone)
        shifts_def = [
            ShiftDefinition(**shift_dict)
            for shift_dict in cast(list[dict[str, Any]], regime.shifts_definition)
        ]

        # Найти смену по номеру
        shift_def = None
        for s_def in shifts_def:
            if s_def.shift_num == shift_number:
                shift_def = s_def
                break

        if not shift_def:
            logger.warning(
                "Shift not found in regime",
                work_regime_id=regime.id,
                shift_number=shift_number,
                available_shifts=[s.shift_num for s in shifts_def],
            )
            return None

        # Получаем время в секундах
        begin_seconds = shift_def.start_time_offset
        end_seconds = shift_def.end_time_offset

        # Вычислить время начала смены
        # Обрабатываем отрицательные значения (смена начинается в предыдущий день)
        if begin_seconds < 0:
            shift_start_date = shift_date - timedelta(days=1)
            begin_seconds_adjusted = begin_seconds + 86400  # +24 часа
        else:
            shift_start_date = shift_date
            begin_seconds_adjusted = begin_seconds

        begin_hours = begin_seconds_adjusted // 3600
        begin_minutes = (begin_seconds_adjusted % 3600) // 60
        begin_secs = begin_seconds_adjusted % 60
        start_time = datetime.combine(shift_start_date, datetime.min.time()).replace(
            hour=begin_hours,
            minute=begin_minutes,
            second=begin_secs,
            tzinfo=tz,
        )

        # Вычислить время конца смены
        # Всегда используем оригинальную дату смены как базовую
        end_hours = end_seconds // 3600
        end_minutes = (end_seconds % 3600) // 60
        end_secs = end_seconds % 60

        if end_seconds >= begin_seconds:
            # Смена в пределах одного дня
            end_time = datetime.combine(shift_date, datetime.min.time()).replace(
                hour=end_hours,
                minute=end_minutes,
                second=end_secs,
                tzinfo=tz,
            )
        else:
            # Смена пересекает полночь (конец на следующий день)
            next_date = shift_date + timedelta(days=1)
            end_time = datetime.combine(next_date, datetime.min.time()).replace(
                hour=end_hours,
                minute=end_minutes,
                second=end_secs,
                tzinfo=tz,
            )

        logger.info(
            "Calculated shift time range",
            work_regime_id=regime.id,
            shift_date=shift_date.isoformat(),
            shift_number=shift_number,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
        )

        return {
            "start_time": start_time,
            "end_time": end_time,
        }

    @staticmethod
    async def get_next_shift(
        work_regime_id: str | None = None,
        current_shift_number: int | None = None,
        current_date: date | None = None,
        timezone: str = "Europe/Moscow",
        db: AsyncSession | None = None,
    ) -> dict[str, Any] | None:
        """Получить следующую смену относительно текущей.

        Args:
            work_regime_id: ID режима работы
            current_shift_number: Номер текущей смены
            current_date: Дата текущей смены (если None - сегодня)
            timezone: Временная зона (default: Europe/Moscow)
            db: Database session

        Returns:
            Словарь с информацией о следующей смене или None если режим неактивен

        Логика:
        - Если текущая смена не последняя на день → вернуть следующую смену на эту же дату
        - Если текущая смена последняя на день → вернуть первую смену следующего дня

        Примечание: Использует секунды (begin_offset_seconds, end_offset_seconds) для вычислений.
        """
        if not work_regime_id or not db or current_shift_number is None:
            return None

        # Получить режим работы
        result = await db.execute(
            select(WorkRegime).where(WorkRegime.id == work_regime_id),
        )
        regime = result.scalar_one_or_none()

        if not regime or not regime.is_active:
            return None

        # Определить текущую дату
        if current_date is None:
            current_date = date.today()

        # Получить shifts_definition
        shifts_def = cast(list[dict[str, Any]], regime.shifts_definition)

        # Отсортировать смены по shift_number
        sorted_shifts = sorted(shifts_def, key=lambda s: s.get("shift_number", 0))

        if not sorted_shifts:
            return None

        # Найти индекс текущей смены
        current_idx = next(
            (
                i
                for i, s in enumerate(sorted_shifts)
                if s.get("shift_number") == current_shift_number
            ),
            None,
        )

        if current_idx is None:
            logger.warning(
                "Current shift number not found",
                work_regime_id=work_regime_id,
                current_shift_number=current_shift_number,
            )
            return None

        # Определить следующую смену
        if current_idx < len(sorted_shifts) - 1:
            # Есть следующая смена на эту же дату
            next_shift_def = sorted_shifts[current_idx + 1]
            target_date = current_date
        else:
            # Последняя смена на день - следующая будет первой сменой следующего дня
            next_shift_def = sorted_shifts[0]
            target_date = current_date + timedelta(days=1)

        # Получить offset в секундах
        # (приоритет: begin_offset_seconds, иначе begin_offset_minutes * 60)
        begin_seconds = next_shift_def.get("begin_offset_seconds")
        if begin_seconds is None:
            begin_minutes = next_shift_def.get("begin_offset_minutes", 0)
            begin_seconds = begin_minutes * 60

        end_seconds = next_shift_def.get("end_offset_seconds")
        if end_seconds is None:
            end_minutes = next_shift_def.get("end_offset_minutes", 0)
            end_seconds = end_minutes * 60

        # Вычислить время начала и конца следующей смены (используя секунды)
        tz = ZoneInfo(timezone)
        begin_hours = begin_seconds // 3600
        begin_mins = (begin_seconds % 3600) // 60
        begin_secs = begin_seconds % 60
        shift_start = datetime.combine(target_date, datetime.min.time()).replace(
            hour=begin_hours,
            minute=begin_mins,
            second=begin_secs,
            tzinfo=tz,
        )

        end_hours = end_seconds // 3600
        end_mins = (end_seconds % 3600) // 60
        end_secs = end_seconds % 60

        if end_seconds >= begin_seconds:
            # Смена в пределах одного дня
            shift_end = datetime.combine(target_date, datetime.min.time()).replace(
                hour=end_hours,
                minute=end_mins,
                second=end_secs,
                tzinfo=tz,
            )
        else:
            # Смена пересекает полночь (конец на следующий день)
            next_date = target_date + timedelta(days=1)
            shift_end = datetime.combine(next_date, datetime.min.time()).replace(
                hour=end_hours,
                minute=end_mins,
                second=end_secs,
                tzinfo=tz,
            )

        return {
            "shift_number": next_shift_def.get("shift_number"),
            "name": next_shift_def.get("name"),
            "begin_offset_seconds": begin_seconds,
            "end_offset_seconds": end_seconds,
            "start_time": shift_start.isoformat(),
            "end_time": shift_end.isoformat(),
            "date": target_date.isoformat(),
            "crosses_midnight": end_seconds < begin_seconds,
        }

    @staticmethod
    async def get_prev_shift(
        work_regime_id: int | None = None,
        current_shift_number: int | None = None,
        current_date: date | None = None,
        timezone: str = "Europe/Moscow",
        db: AsyncSession | None = None,
    ) -> dict[str, Any] | None:
        """Получить предыдущую смену относительно текущей.

        Args:
            work_regime_id: ID режима работы
            current_shift_number: Номер текущей смены
            current_date: Дата текущей смены (если None - сегодня)
            timezone: Временная зона (default: Europe/Moscow)
            db: Database session

        Returns:
            Словарь с информацией о предыдущей смене или None если режим неактивен

        Логика:
        - Если текущая смена не первая на день → вернуть предыдущую смену на эту же дату
        - Если текущая смена первая на день → вернуть последнюю смену предыдущего дня

        Примечание: Использует схему ShiftDefinition
        (shift_num, start_time_offset, end_time_offset).
        """
        if not work_regime_id or not db or current_shift_number is None:
            return None

        # Получить режим работы
        result = await db.execute(
            select(WorkRegime).where(WorkRegime.id == work_regime_id),
        )
        regime = result.scalar_one_or_none()

        if not regime or not regime.is_active:
            return None

        # Определить текущую дату
        if current_date is None:
            current_date = date.today()

        # Получить shifts_definition в формате схемы (shift_num, start_time_offset, end_time_offset)
        shifts_def = [
            ShiftDefinition(**d) for d in cast(list[dict[str, Any]], regime.shifts_definition)
        ]

        # Отсортировать смены по shift_num
        sorted_shifts = sorted(shifts_def, key=lambda s: s.shift_num)

        if not sorted_shifts:
            return None

        # Найти индекс текущей смены
        current_idx = next(
            (i for i, s in enumerate(sorted_shifts) if s.shift_num == current_shift_number),
            None,
        )

        if current_idx is None:
            logger.warning(
                "Current shift number not found",
                work_regime_id=work_regime_id,
                current_shift_number=current_shift_number,
            )
            return None

        # Определить предыдущую смену
        if current_idx > 0:
            # Есть предыдущая смена на эту же дату
            prev_shift_def = sorted_shifts[current_idx - 1]
            target_date = current_date
        else:
            # Первая смена на день - предыдущая будет последней сменой предыдущего дня
            prev_shift_def = sorted_shifts[-1]
            target_date = current_date - timedelta(days=1)

        # Секунды из схемы (start_time_offset, end_time_offset)
        begin_seconds = prev_shift_def.start_time_offset
        end_seconds = prev_shift_def.end_time_offset
        # Обработка отрицательного начала (смена начинается в предыдущий день)
        if begin_seconds < 0:
            shift_start_date = target_date - timedelta(days=1)
            begin_seconds_adjusted = begin_seconds + 86400
        else:
            shift_start_date = target_date
            begin_seconds_adjusted = begin_seconds

        tz = ZoneInfo(timezone)
        begin_hours = begin_seconds_adjusted // 3600
        begin_mins = (begin_seconds_adjusted % 3600) // 60
        begin_secs = begin_seconds_adjusted % 60
        shift_start = datetime.combine(shift_start_date, datetime.min.time()).replace(
            hour=begin_hours,
            minute=begin_mins,
            second=begin_secs,
            tzinfo=tz,
        )

        end_hours = end_seconds // 3600
        end_mins = (end_seconds % 3600) // 60
        end_secs = end_seconds % 60

        if end_seconds >= begin_seconds:
            # Смена в пределах одного дня
            shift_end = datetime.combine(target_date, datetime.min.time()).replace(
                hour=end_hours,
                minute=end_mins,
                second=end_secs,
                tzinfo=tz,
            )
        else:
            # Смена пересекает полночь (конец на следующий день)
            next_date = target_date + timedelta(days=1)
            shift_end = datetime.combine(next_date, datetime.min.time()).replace(
                hour=end_hours,
                minute=end_mins,
                second=end_secs,
                tzinfo=tz,
            )

        return {
            "shift_number": prev_shift_def.shift_num,
            "name": f"Смена {prev_shift_def.shift_num}",
            "begin_offset_seconds": prev_shift_def.start_time_offset,
            "end_offset_seconds": end_seconds,
            "start_time": shift_start.isoformat(),
            "end_time": shift_end.isoformat(),
            "date": target_date.isoformat(),
            "crosses_midnight": end_seconds < begin_seconds,
        }

    @staticmethod
    def get_shift_name_by_number(
        shift_number: int,
        shifts_definition: list[ShiftDefinition],
    ) -> str | None:
        """Получить название смены по её номеру."""
        for shift_def in shifts_definition:
            if shift_def.shift_num == shift_number:
                return f"Смена {shift_def.shift_num}"
        return None
