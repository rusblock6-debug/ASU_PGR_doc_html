"""State Machine для Trip Service.

6 состояний:
1. moving_empty - Движение порожним
2. stopped_empty - Остановка порожним
3. loading - Погрузка
4. moving_loaded - Движение с грузом
5. stopped_loaded - Остановка с грузом
6. unloading - Разгрузка

Триггеры:
- tag - Получение метки локации (основной триггер)
- timer - Таймер бездействия
- manual - Ручной переход
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_client import redis_client
from app.database.base import generate_uuid_vehicle_id
from app.database.models import CycleStateHistory, CycleTagHistory, RouteTask, Trip
from app.enums.vechicle_tag_event import VechicleTagEventEnum
from app.services.place_info import get_load_type, get_place
from app.services.trip_event_publisher import publish_trip_event
from app.services.vehicle_info import get_load_capacity
from app.utils import truncate_datetime_to_seconds


class State(StrEnum):
    """Состояния State Machine."""

    IDLE = "idle"
    MOVING_EMPTY = "moving_empty"
    STOPPED_EMPTY = "stopped_empty"
    LOADING = "loading"
    MOVING_LOADED = "moving_loaded"
    STOPPED_LOADED = "stopped_loaded"
    UNLOADING = "unloading"


class TriggerType(StrEnum):
    """Типы триггеров переходов."""

    TAG = "tag"
    TIMER = "timer"
    MANUAL = "manual"


class StateMachine:
    """State Machine для управления состоянием vehicle и рейсами.

    Состояние хранится в Redis для быстрого доступа.
    История переходов сохраняется в PostgreSQL для аналитики.
    """

    def __init__(self, vehicle_id: int):
        self.vehicle_id = vehicle_id
        # Кэш данных датчиков для определения переходов
        self._sensor_data: dict[str, Any] = {
            "speed": None,
            "weight": None,
            "vibro": None,
            "tag": None,
        }

    async def get_current_state(self) -> dict[str, Any]:
        """Получить текущее состояние State Machine из Redis.

        Returns:
            dict с полями:
            - state: текущее состояние
            - cycle_id: ID активного цикла/рейса (если есть)
            - entity_type: тип сущности в контексте JTI (`cycle` или `trip`)
            - task_id: ID активного задания (если есть)
            - last_tag_id: последний ID тега/метки (строка)
            - last_place_id: последний ID места (число)
            - last_transition: время последнего перехода
        """
        state_data = await redis_client.get_state_machine_data(str(self.vehicle_id))

        if not state_data:
            # Инициализация начального состояния
            state_data = {
                "state": State.STOPPED_EMPTY.value,
                "cycle_id": None,
                "entity_type": None,
                "task_id": None,
                "last_tag_id": None,
                "last_place_id": None,
                "last_transition": cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC))).isoformat(),
            }
            await redis_client.set_state_machine_data(str(self.vehicle_id), state_data)

        state_data.setdefault("unloading", False)
        return state_data

    async def reset_state(self) -> None:
        """Обнулить состояние State Machine: записать в Redis начальное состояние (IDLE, без цикла/рейса)."""
        state_data = {
            "state": State.STOPPED_EMPTY.value,
            "cycle_id": None,
            "entity_type": None,
            "task_id": None,
            "last_tag_id": None,
            "last_place_id": None,
            "last_transition": cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC))).isoformat(),
        }
        await redis_client.set_state_machine_data(str(self.vehicle_id), state_data)

    def _parse_timestamp(self, ts_str: str | None) -> datetime | None:
        """Преобразовать строку ISO в datetime."""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    async def manual_transition(
        self,
        new_state: State,
        reason: str = "manual",
        comment: str = "",
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Ручной переход в новое состояние.

        Args:
            new_state: Целевое состояние
            reason: Причина ручного перехода
            comment: Комментарий оператора
            db: Сессия БД

        Returns:
            dict с информацией о переходе
        """
        # Получить текущее состояние
        current_state_data = await self.get_current_state()
        current_state = State(current_state_data["state"])

        logger.warning(
            "Manual state transition",
            vehicle_id=self.vehicle_id,
            from_state=current_state.value,
            to_state=new_state.value,
            reason=reason,
            comment=comment,
        )

        # Определить действие с циклом/рейсом
        # TODO проверить и убрать если надо
        trip_action = None
        if trip_action is None:
            has_active_trip = await self._has_active_trip(current_state_data)
            if new_state == State.IDLE:
                # Переход в idle - завершить текущий цикл (если есть)
                if current_state_data.get("cycle_id"):
                    trip_action = "end_cycle"
                # ВАЖНО: Сохраняем предыдущее состояние для возврата из простоя
                if current_state != State.IDLE:
                    current_state_data["previous_state"] = current_state.value
            elif new_state == State.MOVING_EMPTY:
                # Переход в moving_empty - завершить текущий цикл (если есть) и создать новый
                if current_state_data.get("cycle_id"):
                    trip_action = "end_cycle"
            elif new_state == State.LOADING:
                if has_active_trip:
                    # Начинаем загрузку, но рейс уже есть - ничего не делаем
                    pass
                else:
                    # Нет активного рейса: если есть цикл - создаем рейс, иначе создаем цикл и рейс
                    trip_action = "start_trip" if current_state_data.get("cycle_id") else "start_cycle_and_trip"
            # UNLOADING: НЕ завершаем рейс при переходе В unloading!
            # Завершение происходит при переходе ИЗ unloading через trip_action="end_cycle"

        # Получить текущую метку из Redis для точного определения точки
        current_tag = await redis_client.get_json(f"trip-service:vehicle:{self.vehicle_id}:current_tag")
        tag_id = current_tag.get("tag_id") if current_tag else current_state_data.get("last_tag_id")

        # Если создаем рейс, обновляем current_state_data с активным заданием
        if trip_action == "start_trip":
            # Получаем активное задание из Redis
            active_task_data = await redis_client.get_active_task(str(self.vehicle_id))
            if active_task_data:
                current_state_data["task_id"] = active_task_data.get("task_id")
                # Сохраняем shift_id из задания в БД
                task_id = active_task_data.get("task_id")
                if task_id and db:
                    result = await db.execute(select(RouteTask).where(RouteTask.id == task_id))
                    task = result.scalar_one_or_none()
                    if task and task.shift_task_id:
                        current_state_data["shift_id"] = str(task.shift_task_id)

            # Обновляем point_id из current_tag
            if current_tag:
                current_state_data["last_tag_id"] = current_tag.get("tag_id")

            logger.info(
                "Manual transition creating planned trip",
                vehicle_id=self.vehicle_id,
                task_id=current_state_data.get("task_id"),
                tag_id=tag_id,
            )

        logger.info(
            "Manual transition with tag",
            vehicle_id=self.vehicle_id,
            new_state=new_state.value,
            tag_id=tag_id,
            has_current_tag=bool(current_tag),
        )

        _ = (current_tag or {}).get("tag_id") or tag_id  # tag_value unused

        # Выполнить переход
        await self._transition_to_state(
            new_state=new_state,
            trigger_type=TriggerType.MANUAL,
            trigger_data={
                "reason": reason,
                "comment": comment,
                "tag_id": tag_id,
                "tag": current_tag.get("tag_id") if current_tag else tag_id,
            },
            trip_action=trip_action,
            current_state_data=current_state_data,
            db=db,
        )

        return {
            "old_state": current_state.value,
            "new_state": new_state.value,
            "trip_action": trip_action,
            "message": f"State changed from {current_state.value} to {new_state.value}",
        }

    async def new_state_action(
        self,
        db: AsyncSession,
    ) -> None:
        """Определить новое состояние на основе текущего состояния, показаний датчиков веса и скорости, типа места.

        Returns:
            tuple: (new_state, trip_action)
            trip_action может быть: "start_cycle", "start_trip", "end_cycle", None
        """
        current_state_data = await self.get_current_state()
        current_state = State(current_state_data["state"])
        tag_data = self._sensor_data.get("tag")
        if tag_data is None:
            return
        speed_data = self._sensor_data.get("speed")
        weight_data = self._sensor_data.get("weight")
        vibro_data = self._sensor_data.get("vibro")
        if not isinstance(speed_data, dict) or not isinstance(weight_data, dict):
            logger.debug(
                "Skipping new_state_action: speed/weight data is not ready",
                vehicle_id=self.vehicle_id,
                has_speed=isinstance(speed_data, dict),
                has_weight=isinstance(weight_data, dict),
            )
            return
        tag_id = tag_data.get("tag_id")
        raw_tag_name = tag_data.get("tag_name")
        tag_name = str(raw_tag_name) if raw_tag_name is not None else None
        place_id = tag_data.get("place_id")
        place_type = tag_data.get("place_type")
        speed_event = speed_data.get("status")
        weight_event = weight_data.get("status")
        raw_weight_value = weight_data.get("value")
        weight_value = float(raw_weight_value) if isinstance(raw_weight_value, int | float) else None
        vibro_event = vibro_data.get("event_type") if isinstance(vibro_data, dict) else None
        unloading = current_state_data.get("unloading", False)

        logger.debug(
            "New state action",
            tag_id=tag_id,
            tag_name=tag_name,
            place_id=place_id,
            place_type=place_type,
            speed_event=speed_event,
            weight_event=weight_event,
            current_state=current_state,
            weight_value=weight_value,
            vibro_event=vibro_event,
            unloading=unloading,
        )
        new_state = None
        trip_action = None

        # Логика переходов State Machine
        if (
            current_state == State.UNLOADING
            and (place_type == "unload" or vibro_event == "weight_fall")
            and weight_value is not None
            and weight_value <= settings.end_cycle_weight
        ):
            remaining_change = await self._save_place_remaining_history(
                place_id=place_id,
                change_type="unloading",
                cycle_id=current_state_data.get("cycle_id"),
                task_id=current_state_data.get("task_id"),
                shift_id=current_state_data.get("shift_id"),
                db=db,
            )
            logger.debug("Remaining change", remaining_change=remaining_change)
            if remaining_change:
                current_state_data["place_remaining_change"] = remaining_change
                logger.info(
                    "place_remaining_change created for unloading",
                    vehicle_id=self.vehicle_id,
                    cycle_id=current_state_data.get("cycle_id"),
                    place_id=place_id,
                    remaining_change=remaining_change,
                )
            else:
                logger.error(
                    "Failed to create place_remaining_change for unloading",
                    vehicle_id=self.vehicle_id,
                    cycle_id=current_state_data.get("cycle_id"),
                    place_id=place_id,
                )

            trip_action = "end_cycle"
            new_state = State.STOPPED_EMPTY
            current_state_data["unloading"] = True
        elif current_state == State.MOVING_EMPTY and speed_event == "stopped" and weight_event == "empty":
            # остановка пустым
            new_state = State.STOPPED_EMPTY
            trip_action = None

        elif (
            current_state == State.STOPPED_EMPTY
            and (place_type == "load" or vibro_event == "weight_rise")
            and speed_event == "stopped"
            and weight_event == "loaded"
        ):
            # Начало погрузки
            logger.info(
                "Loading started - creating trip",
                vehicle_id=self.vehicle_id,
                cycle_id=current_state_data.get("cycle_id"),
                task_id=current_state_data.get("task_id"),
                place_id=place_id,
            )
            new_state = State.LOADING
            trip_action = "start_trip"

        elif current_state == State.LOADING and speed_event == "moving" and weight_event == "loaded":
            # Машина начала движение с грузом
            logger.info(
                "Loading complete, vehicle started moving with load",
                vehicle_id=self.vehicle_id,
                cycle_id=current_state_data.get("cycle_id"),
            )

            # Записываем изменение остатка места погрузки (забрали груз)
            remaining_change = await self._save_place_remaining_history(
                place_id=place_id,
                change_type="loading",
                cycle_id=current_state_data.get("cycle_id"),
                task_id=current_state_data.get("task_id"),
                shift_id=current_state_data.get("shift_id"),
            )
            if remaining_change:
                current_state_data["place_remaining_change"] = remaining_change

            new_state = State.MOVING_LOADED
            trip_action = None

        elif current_state == State.MOVING_LOADED and speed_event == "stopped" and weight_event == "loaded":
            # остановка груженым
            new_state = State.STOPPED_LOADED
            trip_action = None

        elif (
            current_state == State.STOPPED_LOADED
            and (place_type == "unload" or vibro_event == "weight_fall")
            and speed_event == "stopped"
            and weight_event == "loaded"
            and current_state_data.get("unloading", False) is False
        ):
            # разгрузка
            new_state = State.UNLOADING
            trip_action = None

        elif current_state == State.STOPPED_EMPTY and speed_event == "moving" and weight_event == "empty":
            # продолжение движения пустым
            if current_state_data.get("unloading", False) is False:
                new_state = State.MOVING_EMPTY
                trip_action = None
            else:
                # начало движения пустым
                current_state_data["unloading"] = False
                # начало нового цикла
                active_task_data = await redis_client.get_active_task(str(self.vehicle_id))
                if active_task_data:
                    current_state_data["task_id"] = active_task_data.get("task_id")
                    # Сохраняем shift_id из задания в БД
                    task_id = active_task_data.get("task_id")
                    if task_id and db:
                        result = await db.execute(select(RouteTask).where(RouteTask.id == task_id))
                        task = result.scalar_one_or_none()
                        if task and task.shift_task_id:
                            current_state_data["shift_id"] = str(task.shift_task_id)

                logger.info(
                    "Moving started - creating cycle",
                    vehicle_id=self.vehicle_id,
                    cycle_id=current_state_data.get("cycle_id"),
                    task_id=current_state_data.get("task_id"),
                    place_id=place_id,
                )
                new_state = State.MOVING_EMPTY
                trip_action = "start_cycle"

        elif current_state == State.STOPPED_LOADED and speed_event == "moving" and weight_event == "loaded":
            # продолжнеие движения гружоным
            new_state = State.MOVING_LOADED
            trip_action = None

        if new_state is None and trip_action is None:
            return

        if new_state is None:
            # Есть действие для цикла/рейса, но состояние не меняется.
            # Разрешаем _transition_to_state выполнить trip_action.
            new_state = current_state

        # Выполнить переход состояния
        if new_state != current_state or trip_action is not None and not unloading:
            await self._transition_to_state(
                new_state=new_state,
                trigger_type=TriggerType.TAG,
                trigger_data={
                    "tag_id": tag_id,
                    "place_id": place_id,
                    "tag": tag_name,
                },
                trip_action=trip_action,
                current_state_data=current_state_data,
                db=db,
            )

            logger.info(
                "State transition completed",
                vehicle_id=self.vehicle_id,
                old_state=current_state.value,
                new_state=new_state.value,
                trip_action=trip_action,
            )

        else:
            logger.debug(
                "No state change required",
                vehicle_id=self.vehicle_id,
                state=current_state.value,
                tag_id=tag_id,
            )

        logger.debug("Изменено состояние StateMachine")

    async def _transition_to_state(
        self,
        new_state: State,
        trigger_type: TriggerType,
        trigger_data: dict[str, Any],
        trip_action: str | None,
        current_state_data: dict[str, Any],
        save_history: bool = True,
        db: AsyncSession | None = None,
    ) -> None:
        """Выполнить переход в новое состояние.

        - Обновить состояние в Redis
        - Сохранить историю в PostgreSQL
        - Выполнить действия с циклом и рейсом (start/end)
        """
        transition_time = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))

        logger.info(
            "Creating new_state_data for transition",
            vehicle_id=self.vehicle_id,
            new_state=new_state.value,
            **current_state_data,
        )

        new_state_data = {
            **current_state_data,
            "state": new_state.value,
            "last_transition": transition_time.isoformat(),
            "last_tag_id": trigger_data.get("tag_id") or trigger_data.get("tag"),
            "last_place_id": trigger_data.get("place_id"),
        }
        new_state_data.setdefault("entity_type", current_state_data.get("entity_type"))

        logger.info(
            "new_state_data created",
            vehicle_id=self.vehicle_id,
            new_state=new_state.value,
            has_place_remaining_change="place_remaining_change" in new_state_data,
            place_remaining_change=new_state_data.get("place_remaining_change"),
        )

        # ВАЖНО: Если task_id изменился или отсутствует, нужно обновить shift_id
        # Проверяем соответствие task_id и shift_id
        task_id = new_state_data.get("task_id")
        if task_id and db:
            # Проверяем, соответствует ли текущий shift_id текущему task_id
            result = await db.execute(
                select(RouteTask).where(RouteTask.id == task_id),
            )
            task = result.scalar_one_or_none()
            if task:
                # Обновляем shift_id из текущего задания
                if task.shift_task_id:
                    new_state_data["shift_id"] = str(task.shift_task_id)
                else:
                    # Если у задания нет shift_task_id, очищаем shift_id
                    new_state_data.pop("shift_id", None)
            else:
                # Задание не найдено - очищаем shift_id
                new_state_data.pop("shift_id", None)
        elif not task_id:
            # Если task_id отсутствует, очищаем shift_id
            new_state_data.pop("shift_id", None)

        # Сохраняем время перехода в loading/unloading для последующего использования в Trip
        if new_state == State.LOADING:
            new_state_data["loading_timestamp"] = transition_time.isoformat()
        elif new_state == State.UNLOADING:
            new_state_data["unloading_timestamp"] = transition_time.isoformat()

        # Выполнить действия с циклом и рейсом
        cycle_id: str | None = None
        tag: str | None = None
        if trip_action == "start_cycle":
            # Создать новый цикл при переходе в moving_empty/stopped_empty
            place_id = current_state_data.get("last_place_id") or trigger_data.get("place_id")
            task_id = current_state_data.get("task_id")

            cycle_id = await self._start_cycle(
                from_place_id=place_id,
                task_id=task_id,
                db=db,
            )
            new_state_data["cycle_id"] = cycle_id
            new_state_data["entity_type"] = "cycle"

            # Сохраняем shift_id из задания
            if task_id and db:
                result = await db.execute(
                    select(RouteTask).where(RouteTask.id == task_id),
                )
                task = result.scalar_one_or_none()
                if task and task.shift_task_id:
                    new_state_data["shift_id"] = str(task.shift_task_id)

        elif trip_action == "start_cycle_and_trip":
            # idle → loading: Сначала создаем цикл, потом рейс
            place_id = current_state_data.get("last_place_id") or trigger_data.get("place_id")
            tag = current_state_data.get("last_tag_id") or trigger_data.get("tag_id")
            task_id = current_state_data.get("task_id")

            # 1. Создаем цикл
            cycle_id = await self._start_cycle(
                from_place_id=place_id,
                task_id=task_id,
                db=db,
            )
            new_state_data["cycle_id"] = cycle_id
            new_state_data["entity_type"] = "cycle"

            # Сохраняем shift_id из задания
            if task_id and db:
                result = await db.execute(
                    select(RouteTask).where(RouteTask.id == task_id),
                )
                task = result.scalar_one_or_none()
                if task and task.shift_task_id:
                    new_state_data["shift_id"] = str(task.shift_task_id)

            # 2. Создаем рейс внутри цикла
            # При start_cycle_and_trip loading_timestamp = transition_time (переход в loading)
            loading_ts = self._parse_timestamp(current_state_data.get("loading_timestamp")) or transition_time
            trip_result = await self._start_trip(
                place_id=int(place_id) if place_id is not None else 0,
                tag=str(tag) if tag is not None else "",
                task_id=task_id,
                cycle_id=cycle_id,
                state=new_state,
                loading_timestamp=loading_ts if isinstance(loading_ts, datetime) else None,
                db=db,
            )
            new_state_data["cycle_id"] = trip_result["cycle_id"]
            new_state_data["entity_type"] = "trip"
            logger.debug("Создан новый цикл с рейсом", cycle_id=cycle_id)

        elif trip_action == "start_trip":
            # Создать новый рейс при переходе в loading
            # Рейс создается ВНУТРИ цикла
            place_id = current_state_data.get("last_place_id") or trigger_data.get("place_id")
            tag = current_state_data.get("last_tag_id") or trigger_data.get("tag_id")
            task_id = current_state_data.get("task_id")
            cycle_id = str(current_state_data["cycle_id"]) if current_state_data.get("cycle_id") else None

            # loading_timestamp = transition_time (время начала погрузки)
            # start_time тоже = transition_time (будет обновлено при moving_loaded)
            loading_ts = transition_time

            # Если цикл не был создан ранее, создаем его сейчас
            if not cycle_id:
                logger.warning(
                    "Cycle ID missing when creating trip, creating cycle first",
                    vehicle_id=self.vehicle_id,
                    current_state=current_state_data.get("state"),
                )
                cycle_id = await self._start_cycle(
                    from_place_id=place_id,
                    task_id=task_id,
                    db=db,
                )
                new_state_data["cycle_id"] = cycle_id
                new_state_data["entity_type"] = "cycle"

                # Сохраняем shift_id из активного задания
                if task_id:
                    active_task_data = await redis_client.get_active_task(str(self.vehicle_id))
                    if active_task_data and active_task_data.get("shift_task_id"):
                        new_state_data["shift_id"] = str(active_task_data.get("shift_task_id"))
                    elif db:
                        result = await db.execute(
                            select(RouteTask).where(RouteTask.id == task_id),
                        )
                        task = result.scalar_one_or_none()
                        if task and task.shift_task_id:
                            new_state_data["shift_id"] = str(task.shift_task_id)

            trip_result = await self._start_trip(
                place_id=int(place_id) if place_id is not None else 0,
                tag=str(tag) if tag is not None else "",
                task_id=task_id,
                cycle_id=cycle_id,
                state=new_state,
                loading_timestamp=loading_ts if isinstance(loading_ts, datetime) else None,
                db=db,
            )
            new_state_data["cycle_id"] = trip_result["cycle_id"]
            new_state_data["entity_type"] = "trip"

        # Сохраняем place_remaining_change для публикации события
        # Он будет удален после публикации, чтобы не переносился в следующие переходы
        place_remaining_change_for_event = new_state_data.get("place_remaining_change")
        logger.info(
            "Extracted place_remaining_change_for_event",
            vehicle_id=self.vehicle_id,
            new_state=new_state.value,
            has_place_remaining_change=place_remaining_change_for_event is not None,
            place_remaining_change=place_remaining_change_for_event,
            current_state_data_keys=list(current_state_data.keys()),
            new_state_data_keys_before_pop=list(new_state_data.keys()),
        )

        # После завершения разгрузки статус STOPPED_EMPTY не должен относиться к завершенному циклу.
        if (
            trip_action == "end_cycle"
            and new_state == State.STOPPED_EMPTY
            and current_state_data.get("state") == State.UNLOADING.value
        ):
            new_state_data["cycle_id"] = None
            new_state_data["entity_type"] = None

        # Сохранить новое состояние в Redis (без place_remaining_change, чтобы он не переносился)
        new_state_data.pop("place_remaining_change", None)
        await redis_client.set_state_machine_data(str(self.vehicle_id), new_state_data)

        # Создать новый цикл ДО сохранения истории (если нужно)
        if trip_action == "end_cycle" and new_state == State.MOVING_EMPTY:
            place_id = current_state_data.get("last_place_id") or trigger_data.get("place_id")
            task_id = current_state_data.get("task_id")
            new_cycle_id = await self._start_cycle(
                from_place_id=place_id,
                task_id=task_id,
                db=db,
                start_time=transition_time if isinstance(transition_time, datetime) else None,
            )
            # Обновляем состояние с новым cycle_id
            new_state_data["cycle_id"] = new_cycle_id
            new_state_data["entity_type"] = "cycle"

            # Сохраняем shift_id из задания для нового цикла
            if task_id and db:
                result = await db.execute(
                    select(RouteTask).where(RouteTask.id == task_id),
                )
                task = result.scalar_one_or_none()
                if task and task.shift_task_id:
                    new_state_data["shift_id"] = str(task.shift_task_id)

            await redis_client.set_state_machine_data(str(self.vehicle_id), new_state_data)
            logger.debug("Окончание цикла при движении порожним")

        # Сохранить историю в PostgreSQL и получить UUID
        history_id = None
        if db and save_history:
            history_id = await self._save_state_history(
                state=new_state,
                state_data=new_state_data,
                trigger_type=trigger_type,
                trigger_data=trigger_data,
                db=db,
            )
            logger.info(
                "Successfully got history id",
                vehicle_id=self.vehicle_id,
                cycle_id=cycle_id,
                history_id=history_id,
            )

        # ПОСЛЕ сохранения истории - завершаем рейс и цикл
        if trip_action == "end_cycle":
            place_id = current_state_data.get("last_place_id") or trigger_data.get("place_id")
            tag = str(current_state_data.get("last_tag_id") or trigger_data.get("tag_id") or "")
            cycle_id = str(current_state_data["cycle_id"]) if current_state_data.get("cycle_id") else None
            has_active_trip = await self._has_active_trip(current_state_data)

            # Получаем unloading_timestamp из state_data (сохранено при переходе в unloading)
            unloading_ts = self._parse_timestamp(current_state_data.get("unloading_timestamp"))

            # Завершить рейс (если есть)
            if has_active_trip:
                logger.info(
                    "Ending trip before cycle",
                    vehicle_id=self.vehicle_id,
                    cycle_id=cycle_id,
                )
                try:
                    await self._end_trip(
                        cycle_id=cycle_id,
                        place_id=place_id or 0,
                        tag=tag or "",
                        unloading_timestamp=unloading_ts,
                        db=db,
                    )
                    logger.info(
                        "Trip ended successfully, proceeding to end cycle",
                        vehicle_id=self.vehicle_id,
                        cycle_id=cycle_id,
                    )
                except Exception as e:
                    logger.error(
                        "Error ending trip, but continuing with cycle completion",
                        vehicle_id=self.vehicle_id,
                        cycle_id=cycle_id,
                        error=str(e),
                        exc_info=True,
                    )

            # Завершить цикл (ВСЕГДА, даже если рейса не было)
            logger.info(
                "Calling _end_cycle",
                vehicle_id=self.vehicle_id,
                cycle_id=cycle_id,
                to_place_id=place_id,
                has_db=db is not None,
            )
            try:
                # Передаем place_remaining_change в _end_cycle для включения в событие cycle_completed
                await self._end_cycle(
                    cycle_id=cycle_id,
                    to_place_id=place_id,
                    db=db,
                    end_time=transition_time if isinstance(transition_time, datetime) else None,
                    unloading_timestamp=unloading_ts,
                )
                logger.info(
                    "Cycle completion completed successfully",
                    vehicle_id=self.vehicle_id,
                    cycle_id=cycle_id,
                )
            except Exception as e:
                logger.error(
                    "Error ending cycle",
                    vehicle_id=self.vehicle_id,
                    cycle_id=cycle_id,
                    error=str(e),
                    exc_info=True,
                )
        elif (
            trigger_type == TriggerType.MANUAL
            and current_state_data.get("cycle_id")
            and (new_state == State.IDLE or new_state == State.MOVING_EMPTY)
        ):
            # Ручной переход в idle или moving_empty - завершить текущий цикл
            place_id = current_state_data.get("last_place_id") or trigger_data.get("place_id")

            logger.info(
                "Manual cycle completion triggered",
                vehicle_id=self.vehicle_id,
                cycle_id=current_state_data.get("cycle_id"),
                new_state=new_state.value,
                trigger_type=trigger_type.value,
            )

            # Завершить цикл при ручном переходе
            await self._end_cycle(
                cycle_id=current_state_data.get("cycle_id"),
                to_place_id=place_id,
                db=db,
            )

        # IMPORTANT: Publish event AFTER all updates
        # Восстанавливаем place_remaining_change в state_data для публикации события
        if place_remaining_change_for_event:
            new_state_data["place_remaining_change"] = place_remaining_change_for_event
            logger.info(
                "place_remaining_change restored for state_transition event",
                vehicle_id=self.vehicle_id,
                new_state=new_state.value,
                cycle_id=current_state_data.get("cycle_id"),
                place_remaining_change=place_remaining_change_for_event,
            )
        else:
            logger.info(
                "No place_remaining_change to restore for state_transition event",
                vehicle_id=self.vehicle_id,
                new_state=new_state.value,
                cycle_id=current_state_data.get("cycle_id"),
            )

        if save_history:
            await self._publish_state_event(
                state=new_state,
                state_data=new_state_data,
                trigger_type=trigger_type,
                trigger_data=trigger_data,
                history_id=history_id or "",
            )
            logger.debug(
                "Publish state event",
                state=new_state,
                state_data=new_state_data,
                trigger_type=trigger_type,
                trigger_data=trigger_data,
                history_id=history_id or "",
            )

        # Удаляем place_remaining_change после публикации, чтобы он не переносился в следующие переходы
        new_state_data.pop("place_remaining_change", None)
        # Обновляем состояние в Redis без place_remaining_change
        await redis_client.set_state_machine_data(str(self.vehicle_id), new_state_data)

    async def _has_active_trip(self, state_data: dict[str, Any]) -> bool:
        """Проверить, есть ли активный рейс.

        Основные данные берем из state_data (entity_type='trip').
        Дополнительно сверяемся с Redis active_trip, чтобы избежать расхождения при рассинхронизации.
        """
        if state_data.get("entity_type") == "trip":
            return True

        active_trip = await redis_client.get_active_trip(str(self.vehicle_id))
        return bool(active_trip)

    async def _start_cycle(
        self,
        from_place_id: int | None,
        task_id: str | None,
        db: AsyncSession | None = None,
        start_time: datetime | None = None,
    ) -> str:
        """Создать новый цикл через Cycle Manager.

        Args:
            from_place_id: ID места начала цикла (place.id из graph-service)
            task_id: ID активного задания
            db: Database session
            start_time: Время начала цикла (опционально)

        Returns:
            cycle_id: ID созданного цикла
        """
        from app.services.cycle_manager import create_cycle

        # Получить shift_id из задания
        shift_id = None
        if task_id and db:
            result = await db.execute(
                select(RouteTask).where(RouteTask.id == task_id),
            )
            task = result.scalar_one_or_none()
            if task:
                # В новой схеме shift_id соответствует shift_task_id из enterprise-service
                shift_id = str(task.shift_task_id) if task.shift_task_id else None

        cycle_id = await create_cycle(
            vehicle_id=self.vehicle_id,
            from_place_id=from_place_id,
            task_id=task_id,
            shift_id=shift_id,
            db=db,
            start_time=start_time,
        )

        logger.info(
            "Cycle started",
            vehicle_id=self.vehicle_id,
            cycle_id=cycle_id,
            from_place_id=from_place_id,
            task_id=task_id,
        )

        return cycle_id

    async def _start_trip(
        self,
        place_id: int,
        tag: str,
        task_id: str | None,
        cycle_id: str | None,
        state: State | None = None,
        loading_timestamp: datetime | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Создать новый рейс через Trip Manager.

        Рейс создается при переходе в moving_loaded и всегда привязан к циклу.

        Args:
            place_id: ID места начала рейса (place.id из graph-service)
            tag: Метка локации
            task_id: ID задания
            cycle_id: ID цикла, к которому привязан рейс
            state: Текущее состояние State Machine
            loading_timestamp: Время начала погрузки (из state_data)
            db: Database session

        Returns:
            dict: {"cycle_id": str, "trip_type": str, "task_id": Optional[str]}
        """
        if not cycle_id:
            raise ValueError("Cycle ID is required to create a trip")

        from app.services.trip_manager import create_trip

        logger.info(
            "Creating trip with params",
            vehicle_id=self.vehicle_id,
            place_id=place_id,
            tag=tag,
            task_id=task_id,
            cycle_id=cycle_id,
            loading_timestamp=loading_timestamp,
            has_place_id=place_id is not None,
        )

        trip_result = await create_trip(
            vehicle_id=str(self.vehicle_id),
            place_id=place_id,
            tag=tag,
            active_task_id=task_id,
            cycle_id=cycle_id,
            loading_timestamp=loading_timestamp,
            db=db,
        )

        logger.info(
            "Trip started via Trip Manager",
            vehicle_id=self.vehicle_id,
            cycle_id=trip_result["cycle_id"],
            task_id=trip_result.get("task_id"),
            trip_type=trip_result.get("trip_type"),
        )

        return trip_result

    async def _end_trip(
        self,
        cycle_id: str | None,
        place_id: int,
        tag: str,
        unloading_timestamp: datetime | None = None,
        db: AsyncSession | None = None,
    ) -> None:
        """Завершить рейс через Trip Manager."""
        if not cycle_id or not db:
            return

        from app.services.trip_manager import complete_trip

        result = await complete_trip(
            vehicle_id=self.vehicle_id,
            cycle_id=cycle_id,
            place_id=place_id,
            tag=tag,
            db=db,
            unloading_timestamp=unloading_timestamp,
        )

        if result["success"]:
            logger.info(
                "Trip ended via Trip Manager",
                vehicle_id=self.vehicle_id,
                cycle_id=cycle_id,
                trip_type=result.get("trip_type"),
                next_task_id=result.get("next_task_id"),
            )
        else:
            logger.error(
                "Failed to end trip",
                vehicle_id=self.vehicle_id,
                cycle_id=cycle_id,
                error=result.get("message"),
            )

    async def _end_cycle(
        self,
        cycle_id: str | None,
        to_place_id: int | None,
        db: AsyncSession | None = None,
        end_time: datetime | None = None,
        unloading_timestamp: datetime | None = None,
        place_remaining_change: dict[str, Any] | None = None,
    ) -> None:
        """Завершить цикл через Cycle Manager и создать аналитику.

        Args:
            cycle_id: ID цикла
            to_place_id: ID места завершения цикла (place.id из graph-service)
            db: Database session
            end_time: Время завершения цикла (опционально)
            unloading_timestamp: Время начала разгрузки (опционально)
            place_remaining_change: Данные об изменении остатка места (опционально)
        """
        if not cycle_id or not db:
            return

        from app.services.cycle_manager import complete_cycle

        result = await complete_cycle(
            cycle_id=cycle_id,
            to_place_id=to_place_id,
            db=db,
            end_time=end_time,
            unloading_timestamp=unloading_timestamp,
            place_remaining_change=place_remaining_change,
        )

        if result["success"]:
            try:
                from app.services.analytics import finalize_cycle_analytics

                await finalize_cycle_analytics(cycle_id, db)
                logger.info(
                    "Analytics created for completed cycle",
                    vehicle_id=self.vehicle_id,
                    cycle_id=cycle_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to create analytics for completed cycle",
                    vehicle_id=self.vehicle_id,
                    cycle_id=cycle_id,
                    error=str(e),
                )

            logger.info(
                "Cycle ended via Cycle Manager",
                vehicle_id=self.vehicle_id,
                cycle_id=cycle_id,
            )
        else:
            logger.error(
                "Failed to end cycle",
                vehicle_id=self.vehicle_id,
                cycle_id=cycle_id,
                error=result.get("message"),
            )

    async def _publish_sse_event(
        self,
        state: State,
        state_data: dict[str, Any],
        trigger_type: TriggerType,  # TODO не используется
        trigger_data: dict[str, Any],
        history_id: str,
    ) -> None:
        """Публикация события перехода состояния в Redis pub/sub."""
        try:
            import json

            # Берем снепшот текущего рейса из Redis, чтобы не терять контекст
            active_trip = await redis_client.get_active_trip(str(self.vehicle_id))
            cycle_id = state_data.get("cycle_id") or (active_trip or {}).get("cycle_id")
            task_id = state_data.get("task_id") or (active_trip or {}).get("task_id")

            place_id = trigger_data.get("place_id") or state_data.get("last_place_id")

            event_data = {
                "type_name": "cycle_state_history",
                "event_type": "state_transition",
                "id": history_id,
                "timestamp": truncate_datetime_to_seconds(datetime.now(UTC), as_iso_z=True),
                "vehicle_id": self.vehicle_id,
                "cycle_id": cycle_id,
                "state": state.value,
                "source": "system",
                "task_id": task_id,
                "place_id": place_id,
            }

            # Добавляем данные об изменении остатка места (если есть)
            if state_data.get("place_remaining_change"):
                event_data["place_remaining_change"] = state_data["place_remaining_change"]

            if active_trip:
                event_data["active_trip"] = active_trip

            # Публикуем в Redis pub/sub
            channel = f"trip-service:vehicle:{self.vehicle_id}:events"
            if redis_client.redis is None:
                raise RuntimeError("redis_client.redis is not initialized")
            await redis_client.redis.publish(channel, json.dumps(event_data))

            logger.info(
                "📡 State event published to Redis",
                state=state.value,
                vehicle_id=self.vehicle_id,
                channel=channel,
            )

        except Exception as e:
            logger.error(
                "Failed to publish SSE event to Redis",
                state=state.value,
                vehicle_id=self.vehicle_id,
                error=str(e),
            )

    async def _publish_mqtt_event(
        self,
        state: State,
        state_data: dict[str, Any],
        trigger_type: TriggerType,  # TODO не используется
        trigger_data: dict[str, Any],
        history_id: str,
    ) -> None:
        """Публикация события перехода состояния в MQTT trip-service/events."""
        cycle_id = state_data.get("cycle_id")

        try:
            trip_type = state_data.get("trip_type", "unplanned")
            task_id = state_data.get("task_id")
            place_id = trigger_data.get("place_id") or state_data.get("last_place_id") or 0
            place_remaining_change = state_data.get("place_remaining_change")

            logger.info(
                "Publishing MQTT state_transition event",
                vehicle_id=self.vehicle_id,
                state=state.value,
                cycle_id=cycle_id,
                place_id=place_id,
                has_place_remaining_change=place_remaining_change is not None,
                place_remaining_change=place_remaining_change,
                state_data_keys=list(state_data.keys()),
            )

            await publish_trip_event(
                event_type="state_transition",
                cycle_id=cycle_id,
                server_trip_id=task_id,
                trip_type=trip_type,
                vehicle_id=str(self.vehicle_id),
                place_id=place_id,
                state=state.value,
                history_id=history_id,
                place_remaining_change=place_remaining_change,
                unloading_timestamp=self._parse_timestamp(state_data.get("unloading_timestamp")),
            )
        except Exception as mqtt_error:
            logger.warning(
                "Failed to publish state transition to MQTT",
                state=state.value,
                cycle_id=cycle_id,
                error=str(mqtt_error),
            )

    async def _publish_state_event(
        self,
        state: State,
        state_data: dict[str, Any],
        trigger_type: TriggerType,
        trigger_data: dict[str, Any],
        history_id: str,
    ) -> None:
        await self._publish_sse_event(state, state_data, trigger_type, trigger_data, history_id)
        await self._publish_mqtt_event(state, state_data, trigger_type, trigger_data, history_id)

    async def _save_state_history(
        self,
        state: State,
        state_data: dict[str, Any],
        trigger_type: TriggerType,
        trigger_data: dict[str, Any],
        db: AsyncSession,
    ) -> str:
        """Сохранить историю перехода состояния цикла."""
        history_id = generate_uuid_vehicle_id(self.vehicle_id)

        place_id = trigger_data.get("place_id") or state_data.get("last_place_id")
        task_id = state_data.get("task_id") or trigger_data.get("task_id")

        if trigger_type == TriggerType.MANUAL:
            source = "dispatcher"
        else:
            source = state_data.get("source", "system")

        if source not in ["dispatcher", "system"]:
            source = "system"

        ts = self._parse_timestamp(state_data.get("last_transition"))
        if ts is None:
            ts = cast(datetime, truncate_datetime_to_seconds(datetime.now(UTC)))

        history = CycleStateHistory(
            id=history_id,
            timestamp=ts,
            vehicle_id=self.vehicle_id,
            cycle_id=state_data.get("cycle_id"),
            state=state.value,
            state_data=state_data,
            place_id=place_id,
            source=source,
            task_id=task_id,
            trigger_type=trigger_type.value,
            trigger_data=trigger_data,
        )

        db.add(history)
        await db.commit()

        return history_id

    async def _save_tag_history(
        self,
        tag_id: int | str,
        tag_name: str,
        place_id: int | None,
        place_name: str,
        place_type: str,
        cycle_id: str | None,
        db: AsyncSession,
        tag_event: VechicleTagEventEnum = VechicleTagEventEnum.entry,
    ) -> None:
        history_id = generate_uuid_vehicle_id(self.vehicle_id)

        history = CycleTagHistory(
            id=history_id,
            timestamp=truncate_datetime_to_seconds(datetime.now(UTC)),
            vehicle_id=self.vehicle_id,
            cycle_id=cycle_id,
            tag_id=int(tag_id),
            tag_name=tag_name,
            place_id=place_id,
            place_name=place_name,
            place_type=place_type,
            tag_event=tag_event,
        )
        try:
            db.add(history)
            await db.commit()
        except Exception as e:
            logger.error(
                "CycleTagHistory save failed",
                vehicle_id=self.vehicle_id,
                cycle_id=cycle_id,
                tag_id=tag_id,
                error=str(e),
            )
            await db.rollback()
            raise

        logger.info(
            "Tag history saved - point_id changed",
            vehicle_id=self.vehicle_id,
            cycle_id=cycle_id,
            tag_id=tag_id,
            tag_name=tag_name,
            place_id=place_id,
            place_name=place_name,
            place_type=place_type,
            history_id=history_id,
        )

    async def _set_tag_event_to_entry(self, db: AsyncSession) -> None:
        smtp = (
            select(CycleTagHistory)
            .where(CycleTagHistory.vehicle_id == self.vehicle_id)
            .order_by(CycleTagHistory.timestamp.desc())
            .limit(1)
        )
        record = await db.scalar(smtp)
        if record is None:
            return
        tag_history = CycleTagHistory(
            id=generate_uuid_vehicle_id(self.vehicle_id),
            timestamp=truncate_datetime_to_seconds(datetime.now(UTC)),
            vehicle_id=record.vehicle_id,
            cycle_id=record.cycle_id,
            place_id=record.place_id,
            place_name=record.place_name,
            place_type=record.place_type,
            tag_id=record.tag_id,
            tag_name=record.tag_name,
            tag_event=VechicleTagEventEnum.exit,
        )
        db.add(tag_history)
        await db.commit()

    async def _save_place_remaining_history(
        self,
        place_id: int | None,
        change_type: str,
        cycle_id: str | None,
        task_id: str | None = None,
        shift_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any] | None:
        """Сформировать событие изменения остатка места (для публикации в MQTT).

        В server mode фактическая запись в БД делается в `app/app/services/event_handlers.py`
        (см. `handle_place_remaining_change`). В bort mode мы только формируем payload.

        Args:
            place_id: ID места (place.id из graph-service). Если None — событие не формируем.
            change_type: Тип изменения ('loading' - забрали с места, 'unloading' - привезли на место)
            cycle_id: ID текущего цикла
            task_id: ID задания (опционально, для единообразия сохраняется в объекте)
            shift_id: ID смены (опционально, для единообразия сохраняется в объекте)
            db: Database session (опционально)

        Returns:
            Dict с данными изменения остатка или None при ошибке:
            {
                "id": str,
                "place_id": int,
                "change_type": str,
                "change_amount": float,
                "source": str,
                "task_id": Optional[str],
                "shift_id": Optional[str],
            }
        """
        # Получаем грузоподъёмность машины
        load_capacity = await get_load_capacity(self.vehicle_id)

        if load_capacity is None:
            logger.error(
                "Load capacity is None",
                vehicle_id=self.vehicle_id,
                change_type=change_type,
            )
            return None

        data_place_id = None

        if change_type == "unloading" and cycle_id and db:
            try:
                trip_result = await db.execute(
                    select(Trip).where(Trip.cycle_id == cycle_id),
                )
                trip = trip_result.scalar_one_or_none()
                if trip and trip.loading_place_id:
                    data_place_id = trip.loading_place_id
            except Exception as e:
                logger.error(
                    "Failed to load trip for unloading place data",
                    vehicle_id=self.vehicle_id,
                    cycle_id=cycle_id,
                    error=str(e),
                    exc_info=True,
                )
                return None

        else:
            data_place_id = place_id

        if place_id is None or data_place_id is None:
            logger.warning(
                "Skipping place_remaining_change: place_id or data_place_id is None",
                vehicle_id=self.vehicle_id,
                change_type=change_type,
                cycle_id=cycle_id,
            )
            return None

        place_info = await get_place(place_id=data_place_id)

        if place_info is None or place_info.get("cargo_type") is None:
            logger.error(
                "Cargo type is None",
                vehicle_id=self.vehicle_id,
                place_id=data_place_id,
                change_type=change_type,
            )
            return None

        cargo_type_info = await get_load_type(int(place_info["cargo_type"]))

        if cargo_type_info is None:
            logger.error(
                "Cargo type info is None",
                vehicle_id=self.vehicle_id,
                place_id=data_place_id,
                cargo_type=place_info.get("cargo_type"),
                change_type=change_type,
            )
            return None

        density = cargo_type_info.get("density")
        if density is None:
            logger.error(
                "Density is None in cargo_type_info",
                vehicle_id=self.vehicle_id,
                place_id=data_place_id,
                cargo_type=place_info.get("cargo_type"),
                change_type=change_type,
            )
            return None

        # Рассчитываем объем: объем = грузоподъемность / плотность
        if density == 0:
            logger.error(
                "Density is zero, cannot calculate volume",
                vehicle_id=self.vehicle_id,
                place_id=data_place_id,
                cargo_type=place_info.get("cargo_type"),
                change_type=change_type,
            )
            return None

        base_amount = float(load_capacity) / float(density) if load_capacity is not None else 0.0

        # Определяем изменение остатка (float):
        # - При погрузке (loading): забираем с места → остаток уменьшается (отрицательное значение)
        # - При разгрузке (unloading): привозим на место → остаток увеличивается (положительное значение)
        # Если load_capacity неизвестна, используем 0.0 (изменение неизвестно, но факт операции можно зафиксировать)
        if change_type == "loading":
            change_amount = -abs(base_amount)
        elif change_type == "unloading":
            change_amount = abs(base_amount)
        else:
            logger.error(
                "Invalid change_type for place remaining history",
                vehicle_id=self.vehicle_id,
                change_type=change_type,
            )
            return None

        record_id = generate_uuid_vehicle_id(self.vehicle_id)
        result = {
            "id": record_id,
            "place_id": place_id,
            "change_type": change_type,
            "change_amount": change_amount,
            "source": "system",
        }

        # Сохраняем task_id и shift_id в объекте для единообразия (loading и unloading)
        if task_id is not None:
            result["task_id"] = task_id
        if shift_id is not None:
            result["shift_id"] = shift_id

        return result

    # ========================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ ОТ ДАТЧИКОВ (MQTT)
    # ========================================================================

    async def handle_speed_event(self, speed_data: dict[str, Any], db: AsyncSession | None = None) -> None:
        """Обработка события изменения скорости.

        Args:
            speed_data: {"status": "moving" | "stopped", "value": float, "timestamp": float}
            db: Database session
        """
        self._sensor_data["speed"] = speed_data
        current_state_data = await self.get_current_state()
        current_state = State(current_state_data["state"])

        # Отслеживание состояния
        if db:
            await self.new_state_action(db)

        logger.debug(
            "Speed event",
            vehicle_id=self.vehicle_id,
            status=speed_data.get("status"),
            current_state=current_state.value,
        )

    async def handle_weight_event(self, weight_data: dict[str, Any], db: AsyncSession | None = None) -> None:
        """Обработка события изменения веса.

        Args:
            weight_data: {"status": "loaded" | "empty", "value": float, "avg_weight": float, "timestamp": float}
            db: Database session
        """
        # Нормализуем поле value
        current_weight = weight_data.get("avg_weight", weight_data.get("value", 0))
        weight_data["value"] = current_weight

        # Вычисляем дельту веса для определения начала погрузки/разгрузки
        # TODO: убрать после демо!!!
        prev_weight_data = self._sensor_data.get("weight")
        prev_weight = prev_weight_data.get("value", 0) if prev_weight_data else 0
        weight_delta = current_weight - prev_weight
        self._sensor_data["weight_delta"] = weight_delta

        self._sensor_data["weight"] = weight_data

        logger.debug(
            "Weight event",
            vehicle_id=self.vehicle_id,
            status=weight_data.get("status"),
            value=current_weight,
            delta=weight_delta,
        )

        # Вес используется в комбинации с vibro для определения loading/unloading
        # Проверяем условия после получения обновленного значения
        # await self._check_loading_unloading_transitions(db)

    async def handle_vibro_event(self, vibro_data: dict[str, Any], db: AsyncSession | None = None) -> None:
        """Обработка события вибродатчика.

        Args:
            vibro_data: {"status": "active" | "inactive", "delta_weight": float, "duration": float, "timestamp": float}
            db: Database session
        """
        self._sensor_data["vibro"] = vibro_data
        current_state_data = await self.get_current_state()
        current_state = State(current_state_data["state"])

        logger.debug(
            "Vibro event",
            vehicle_id=self.vehicle_id,
            status=vibro_data.get("status"),
            current_state=current_state.value,
        )

        # Проверяем переходы loading/unloading согласно таблице
        # await self._check_loading_unloading_transitions(db)

    async def handle_fuel_event(self, fuel_data: dict[str, Any], db: AsyncSession | None = None) -> None:
        """Обработка события заправки.

        === ЗАПРАВКА ВРЕМЕННО ОТКЛЮЧЕНА ===
        TODO: Разобраться с логикой заправки - вызывает чередование состояний

        Во время остановки (stopped_empty или stopped_loaded) проверяем статус заправки.
        При начале заправки (status='refueling') переходим в idle с причиной 'refueling'.
        При окончании заправки (status='consumption') возвращаемся в предыдущее состояние остановки.
        Во время заправки игнорируем все события движения/остановки - ждем только сигнала consumption.

        Args:
            fuel_data: {"status": "refueling" | "consumption" | ..., "value": float, "timestamp": float}
            db: Database session
        """
        fuel_status = fuel_data.get("status")
        current_state_data = await self.get_current_state()
        current_state = State(current_state_data["state"])

        logger.debug(
            "Fuel event",
            vehicle_id=self.vehicle_id,
            status=fuel_status,
            current_state=current_state.value,
        )

        # === ЗАПРАВКА ВРЕМЕННО ОТКЛЮЧЕНА ===
        # TODO: Разобраться с логикой заправки - вызывает чередование состояний
        # # Проверяем начало заправки только в состояниях остановки
        # if fuel_status == "refueling":
        #     if current_state == State.STOPPED_EMPTY or current_state == State.STOPPED_LOADED:
        #         # Сохраняем предыдущее состояние для возврата после заправки
        #         current_state_data["previous_state"] = current_state.value
        #         current_state_data["idle_reason"] = "refueling"
        #
        #         logger.info(
        #             "Refueling started, transitioning to idle",
        #             vehicle_id=self.vehicle_id,
        #             from_state=current_state.value,
        #             previous_state=current_state.value
        #         )
        #
        #         # Переходим в idle с причиной заправки
        #         await self._transition_to_state(
        #             new_state=State.IDLE,
        #             trigger_type=TriggerType.TAG,
        #             trigger_data={
        #                 **fuel_data,
        #                 "reason": "refueling"
        #             },
        #             trip_action=None,  # Не завершаем цикл при заправке
        #             current_state_data=current_state_data,
        #             db=db
        #         )
        #     elif current_state == State.IDLE and current_state_data.get("idle_reason") == "refueling":
        #         # Уже в idle из-за заправки - ничего не делаем
        #         logger.debug(
        #             "Already in refueling idle state",
        #             vehicle_id=self.vehicle_id
        #         )

        # # Проверяем окончание заправки - ТОЛЬКО по статусу consumption
        # elif fuel_status == "consumption" and current_state == State.IDLE and
        # current_state_data.get("idle_reason") == "refueling":
        #     previous_state = current_state_data.get("previous_state")
        #     if previous_state:
        #         previous_state_enum = State(previous_state)
        #
        #         logger.debug(
        #             "Refueling completed (consumption), returning to previous stopped state",
        #             vehicle_id=self.vehicle_id,
        #             previous_state=previous_state,
        #             fuel_status=fuel_status
        #         )
        #
        #         # Очищаем reason и previous_state после возврата
        #         current_state_data.pop("idle_reason", None)
        #         current_state_data.pop("previous_state", None)
        #
        #         await self._transition_to_state(
        #             new_state=previous_state_enum,
        #             trigger_type=TriggerType.TAG,
        #             trigger_data=fuel_data,
        #             trip_action=None,
        #             current_state_data=current_state_data,
        #             db=db
        #         )

    async def handle_tag_event(self, tag_data: dict[str, Any], db: AsyncSession | None = None) -> None:
        """Обработка события изменения метки (локации).

        Args:
            tag_data: {"tag_id": str, "tag_name": str, "place_id": int,
                       "place_name": str, "place_type": str, "timestamp": float}
            db: Database session
        """
        self._sensor_data["tag"] = tag_data
        tag_id = tag_data.get("tag_id")
        raw_tag_name = tag_data.get("tag_name")
        tag_name = str(raw_tag_name) if raw_tag_name is not None else None
        place_id = tag_data.get("place_id")  # ID места из graph-service
        place_type = tag_data.get("place_type")
        raw_place_name = tag_data.get("place_name")
        place_name = str(raw_place_name) if raw_place_name is not None else None

        logger.debug(
            "Tag event",
            vehicle_id=self.vehicle_id,
            place_id=place_id,
            place_name=place_name,
            place_type=place_type,
            tag_id=tag_id,
            tag_name=tag_name,
        )

        current_state_data = await self.get_current_state()
        last_event = current_state_data.get("last_event") if current_state_data.get("last_event") else None

        # new_state, trip_action = self.new_state_action(
        #     current_state,
        #     place_type,
        #     weight_status,
        #     speed_status,
        # )

        cycle_id = current_state_data.get("cycle_id")
        if tag_id is None and last_event == VechicleTagEventEnum.exit:
            return

        elif tag_id is None and last_event == VechicleTagEventEnum.entry and cycle_id is not None:
            if db:
                await self._set_tag_event_to_entry(db)
            current_state_data["last_event"] = VechicleTagEventEnum.exit
            await redis_client.set_state_machine_data(str(self.vehicle_id), current_state_data)
            return
        elif tag_id is not None and last_event == VechicleTagEventEnum.entry:
            return

        if tag_id is None:
            return

        # Сохраняем метку в Redis
        await redis_client.set_json(f"trip-service:vehicle:{self.vehicle_id}:current_tag", tag_data)

        # Публикуем изменение метки
        await redis_client.publish(f"trip-service:vehicle:{self.vehicle_id}:current_tag:changes", tag_data)

        # Сохраняем tag_id и place_id в current_state_data сразу при получении тега
        # Это важно для того, чтобы при создании рейса были доступны данные о месте погрузки
        current_state_data["last_tag_id"] = int(tag_id)
        # last_place_id только int или None (tag_data может содержать place_name вместо place_id)
        current_state_data["last_place_id"] = place_id
        current_state_data["last_event"] = VechicleTagEventEnum.entry
        # Сохраняем обновленное состояние в Redis
        await redis_client.set_state_machine_data(str(self.vehicle_id), current_state_data)

        # Сохраняем только если tag_id не None (машина в зоне точки) и есть активный цикл
        if cycle_id and db:
            await self._save_tag_history(
                tag_id=int(tag_id),
                tag_name=tag_name or "",
                place_id=place_id,
                place_name=place_name or "",
                place_type=place_type or "",
                cycle_id=cycle_id,
                db=db,
            )

        # Определить новое состояние на основе текущего состояния и тега
        # new_state, trip_action = await self._determine_new_state(
        #     current_state=current_state,
        #     tag=tag_name,
        # )


# Глобальный реестр State Machine для каждого vehicle
_state_machines: dict[int, StateMachine] = {}


def get_state_machine(vehicle_id: int) -> StateMachine:
    """Получить State Machine для vehicle.

    Создает новый экземпляр если не существует.
    """
    if vehicle_id not in _state_machines:
        _state_machines[vehicle_id] = StateMachine(vehicle_id)

    return _state_machines[vehicle_id]
