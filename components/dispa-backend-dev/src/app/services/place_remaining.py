"""Сервис для работы с остатками на местах."""

import uuid
from datetime import datetime
from typing import Any, TypedDict, cast

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PlaceRemainingHistoryCreate
from app.database.models import PlaceRemainingHistory, Trip
from app.enums import RemainingChangeTypeEnum
from app.services.event_handlers import handle_place_remaining_change
from app.services.place_info import (
    get_load_type,
    get_place,
    get_place_stock,
    recalculate_and_update_place_stock,
)


class _LoadTypeInfo(TypedDict):
    density: Any


class _PlaceInfo(TypedDict):
    cargo_type: Any | None


class PlaceRemainingService:
    """Сервис управления историей остатков на местах."""

    @staticmethod
    def _round_change_volume(change_volume: float) -> float:
        return round(change_volume, 1)

    @staticmethod
    def _round_change_weight(change_weight: float) -> float:
        return round(change_weight, 3)

    @staticmethod
    def _float_matches(
        actual_value: float,
        expected_value: float,
        *,
        abs_tol: float = 0.05,
        rel_tol: float = 0.0,
    ) -> bool:
        tolerance = max(abs_tol, abs(expected_value) * rel_tol)
        return abs(actual_value - expected_value) <= tolerance

    @staticmethod
    def _sign(value: float) -> int:
        if value == 0:
            return 0
        return 1 if value > 0 else -1

    @staticmethod
    def _apply_sign(value: float, sign_source: float) -> float:
        if PlaceRemainingService._sign(sign_source) == 0:
            return 0.0
        return abs(value) if sign_source > 0 else -abs(value)

    def _weight_matches_volume(self, change_volume: float, change_weight: float, density: float) -> bool:
        """Проверка согласованности объёма и веса по плотности."""
        expected_weight = abs(change_volume) * density
        return self._float_matches(
            actual_value=abs(change_weight),
            expected_value=expected_weight,
            abs_tol=0.05,
            rel_tol=0.02,
        )

    def _calculate_weight_from_volume(self, change_volume: float, density: float) -> float:
        expected_weight = abs(change_volume) * density
        rounded_weight = self._round_change_weight(expected_weight)
        return self._apply_sign(rounded_weight, change_volume)

    def _calculate_volume_from_weight(
        self,
        change_weight: float,
        change_type: RemainingChangeTypeEnum,
        density: float,
    ) -> float:
        calculated_volume = self._round_change_volume(abs(change_weight) / density)
        if change_type == RemainingChangeTypeEnum.loading:
            return -calculated_volume
        return calculated_volume

    def _validate_weight_for_volume_restore(
        self,
        *,
        change_type: RemainingChangeTypeEnum,
        change_weight: float,
    ) -> None:
        if change_weight == 0:
            return

        expected_weight_sign = -1 if change_type == RemainingChangeTypeEnum.loading else 1
        if self._sign(change_weight) == expected_weight_sign:
            return

        expected_sign_label = "отрицательным" if expected_weight_sign < 0 else "положительным"
        raise ValueError(
            f"Для change_type={change_type.value} change_weight должен быть {expected_sign_label}",
        )

    def _validate_change_volume_and_weight(
        self,
        *,
        change_volume: float,
        change_weight: float | None,
        density: float | None,
    ) -> None:
        if change_weight is None:
            return

        if change_volume == 0:
            if change_weight != 0:
                raise ValueError("При нулевом change_volume ожидается нулевой change_weight")
            return

        if density is None:
            return

        if self._sign(change_weight) != self._sign(change_volume):
            raise ValueError("change_weight должен иметь тот же знак, что и change_volume")

        if not self._weight_matches_volume(
            change_volume=change_volume,
            change_weight=change_weight,
            density=density,
        ):
            raise ValueError(
                "change_volume и change_weight не согласуются с плотностью груза (load_type_id / место погрузки)",
            )

    async def _density_for_load_type_id(self, load_type_id: int | None) -> float | None:
        if load_type_id is None:
            return None
        load_type_info = await get_load_type(load_type_id)
        if load_type_info is None:
            return None

        density_raw = cast(_LoadTypeInfo, load_type_info)["density"]
        try:
            density = float(density_raw)
        except (TypeError, ValueError):
            return None

        if density <= 0:
            return None
        return density

    async def _load_type_id_for_place_id(
        self,
        place_id: int | None,
    ) -> int | None:
        """Получить load_type_id по месту."""
        if place_id is None:
            return None

        place_info = await get_place(place_id)
        if place_info is None:
            return None

        load_type_raw = cast(_PlaceInfo, place_info)["cargo_type"]
        try:
            load_type_id = int(load_type_raw) if load_type_raw is not None else None
        except (TypeError, ValueError):
            load_type_id = None

        return load_type_id

    async def _density_and_load_type_for_place_id(
        self,
        place_id: int | None,
    ) -> tuple[float | None, int | None]:
        """Плотность и load_type_id по месту погрузки (cargo_type места)."""
        load_type_id = await self._load_type_id_for_place_id(place_id)
        if load_type_id is None:
            return None, None

        density = await self._density_for_load_type_id(load_type_id)
        if density is None:
            return None, load_type_id

        return density, load_type_id

    async def _resolve_effective_load_type_id(
        self,
        db: AsyncSession,
        data: PlaceRemainingHistoryCreate,
    ) -> int | None:
        if data.load_type_id is not None:
            return data.load_type_id

        loading_place_id = await self._loading_place_id_for_history_row(
            db=db,
            change_type=data.change_type,
            place_id=data.place_id,
            cycle_id=data.cycle_id,
        )
        return await self._load_type_id_for_place_id(loading_place_id)

    async def _loading_place_id_for_history_row(
        self,
        db: AsyncSession,
        change_type: RemainingChangeTypeEnum,
        place_id: int,
        cycle_id: str | None,
    ) -> int | None:
        """Место погрузки для определения типа груза и плотности (как в update_change_fields_for_trip)."""
        if change_type == RemainingChangeTypeEnum.manual:
            return place_id
        if cycle_id:
            trip_result = await db.execute(select(Trip).where(Trip.cycle_id == cycle_id))
            trip = trip_result.scalar_one_or_none()
            if trip is not None and trip.loading_place_id is not None:
                return trip.loading_place_id
        if change_type == RemainingChangeTypeEnum.loading:
            return place_id
        return None

    async def _normalize_history_create(
        self,
        db: AsyncSession,
        data: PlaceRemainingHistoryCreate,
    ) -> PlaceRemainingHistoryCreate:
        """Нормализовать объём/вес и при необходимости дополнить данные по типу груза."""
        is_trip_change = data.change_type in (
            RemainingChangeTypeEnum.loading,
            RemainingChangeTypeEnum.unloading,
        )
        has_target_stock = data.target_stock is not None
        change_volume = data.change_volume
        change_weight = data.change_weight
        effective_load_type_id = data.load_type_id
        calculated_target_volume: float | None = None
        density: float | None = None

        # 1. Проверяем входные данные и собираем обязательный контекст.
        if has_target_stock and data.change_type != RemainingChangeTypeEnum.manual:
            raise ValueError("target_stock допускается только при change_type=manual")

        if data.change_type == RemainingChangeTypeEnum.manual and not has_target_stock and change_volume is None:
            raise ValueError(
                "Для change_type=manual нужен change_volume или target_stock",
            )

        if is_trip_change and change_volume is None and change_weight is None:
            raise ValueError(
                "Для change_type loading/unloading нужен change_volume или change_weight",
            )

        if has_target_stock:
            target_stock = data.target_stock
            if target_stock is None:
                raise ValueError("target_stock обязателен, если has_target_stock=True")
            current_stock = await get_place_stock(place_id=data.place_id, db=db)
            calculated_target_volume = self._round_change_volume(target_stock - current_stock)

            if change_volume is not None:
                rounded_input_volume = self._round_change_volume(change_volume)
                if not self._float_matches(
                    actual_value=rounded_input_volume,
                    expected_value=calculated_target_volume,
                    abs_tol=0.05,
                ):
                    raise ValueError("change_volume не согласуется с target_stock и текущим остатком места")

        if is_trip_change or effective_load_type_id is not None:
            effective_load_type_id = await self._resolve_effective_load_type_id(db=db, data=data)

        if effective_load_type_id is not None:
            density = await self._density_for_load_type_id(effective_load_type_id)

        if is_trip_change and (effective_load_type_id is None or density is None):
            raise ValueError(
                "Для change_type loading/unloading должны определяться load_type_id "
                "и плотность груза, чтобы сохранить change_weight",
            )

        if change_volume is None and calculated_target_volume is None and (change_weight is None or density is None):
            raise ValueError(
                "Нельзя восстановить change_volume по change_weight без плотности груза "
                "(место погрузки / load_type_id)",
            )

        if change_volume is None and calculated_target_volume is None:
            if change_weight is None:
                raise ValueError("change_weight обязателен для восстановления change_volume")
            self._validate_weight_for_volume_restore(
                change_type=data.change_type,
                change_weight=change_weight,
            )

        # 2. Вычисляем и валидируем итоговые значения.
        if calculated_target_volume is not None:
            change_volume = calculated_target_volume
            change_weight = None
        elif change_volume is None:
            if change_weight is None:
                raise ValueError("change_weight обязателен для вычисления change_volume")
            if density is None:
                raise ValueError("density обязательна для вычисления change_volume из change_weight")
            change_volume = self._calculate_volume_from_weight(
                change_weight=change_weight,
                change_type=data.change_type,
                density=density,
            )

        normalized_change_volume = self._round_change_volume(change_volume)
        self._validate_change_volume_and_weight(
            change_volume=normalized_change_volume,
            change_weight=change_weight,
            density=density,
        )

        # 3. После проверок только формируем нормализованный результат.
        if normalized_change_volume == 0:
            return data.model_copy(
                update={
                    "change_volume": 0.0,
                    "change_weight": 0.0,
                    "load_type_id": effective_load_type_id,
                },
            )

        normalized_change_weight: float | None = None
        if change_weight is not None:
            normalized_change_weight = self._round_change_weight(change_weight)
        elif density is not None:
            normalized_change_weight = self._calculate_weight_from_volume(
                change_volume=normalized_change_volume,
                density=density,
            )

        normalized_data: dict[str, Any] = {
            "change_volume": normalized_change_volume,
            "load_type_id": effective_load_type_id,
            "change_weight": normalized_change_weight,
        }

        return data.model_copy(update=normalized_data)

    async def _notify_graph_for_history(
        self,
        db: AsyncSession,
        history: PlaceRemainingHistory,
    ) -> None:
        place_remaining_data = {
            "id": history.id,
            "place_id": history.place_id,
            "change_type": history.change_type.value,
            "change_volume": history.change_volume,
            "load_type_id": history.load_type_id,
            "change_weight": history.change_weight,
            "source": history.source,
            "task_id": history.task_id,
            "shift_id": history.shift_id,
            "cycle_id": history.cycle_id,
        }
        context_data = {
            "vehicle_id": history.vehicle_id,
            "cycle_id": history.cycle_id,
            "task_id": history.task_id,
            "shift_id": history.shift_id,
        }
        await handle_place_remaining_change(
            pr_data=place_remaining_data,
            context_data=context_data,
            event_timestamp=history.timestamp,
            db=db,
        )

    async def create_history(
        self,
        db: AsyncSession,
        data: PlaceRemainingHistoryCreate,
        notify_graph: bool = True,
        *,
        commit: bool = True,
    ) -> PlaceRemainingHistory:
        """Создать запись истории и опционально уведомить graph-service.

        commit=False: только flush в текущей транзакции (для пары loading/unloading с одним commit).
        При commit=False параметр notify_graph должен быть False — уведомление после общего commit.
        """
        if not commit and notify_graph:
            raise ValueError("При commit=False укажите notify_graph=False; вызовите уведомление после commit")

        data = await self._normalize_history_create(db, data)
        change_volume = data.change_volume
        if change_volume is None:
            raise ValueError("После нормализации должен быть задан change_volume")

        history_id = str(uuid.uuid4())

        history = PlaceRemainingHistory(
            id=history_id,
            place_id=data.place_id,
            change_type=data.change_type,
            change_volume=round(change_volume, 1),
            load_type_id=data.load_type_id,
            change_weight=round(data.change_weight, 3) if data.change_weight is not None else None,
            timestamp=data.timestamp,
            cycle_id=data.cycle_id,
            task_id=data.task_id,
            shift_id=data.shift_id,
            vehicle_id=data.vehicle_id,
            source=data.source,
        )

        db.add(history)
        if commit:
            await db.commit()
            await db.refresh(history)
            if notify_graph:
                await self._notify_graph_for_history(db, history)
        else:
            await db.flush()

        return history

    async def create_trip_loading_unloading_pair(
        self,
        db: AsyncSession,
        loading_data: PlaceRemainingHistoryCreate,
        unloading_data: PlaceRemainingHistoryCreate,
        notify_graph: bool = True,
    ) -> tuple[PlaceRemainingHistory, PlaceRemainingHistory]:
        """Создать две записи loading/unloading одной транзакцией (один commit).

        Если вторая запись отклонена валидацией, первая не остаётся в БД.
        """
        loading_rec = await self.create_history(
            db,
            loading_data,
            notify_graph=False,
            commit=False,
        )
        unloading_rec = await self.create_history(
            db,
            unloading_data,
            notify_graph=False,
            commit=False,
        )
        await db.commit()
        await db.refresh(loading_rec)
        await db.refresh(unloading_rec)
        if notify_graph:
            await self._notify_graph_for_history(db, loading_rec)
            await self._notify_graph_for_history(db, unloading_rec)
        return loading_rec, unloading_rec

    async def get_by_timestamp_range(
        self,
        db: AsyncSession,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> list[PlaceRemainingHistory]:
        """Получить все записи PlaceRemainingHistory в указанном временном диапазоне.

        Args:
            db: Database session
            start_timestamp: Начало временного диапазона (включительно)
            end_timestamp: Конец временного диапазона (включительно)

        Returns:
            Список записей PlaceRemainingHistory, отсортированных по timestamp
        """
        query = (
            select(PlaceRemainingHistory)
            .where(PlaceRemainingHistory.timestamp >= start_timestamp)
            .where(PlaceRemainingHistory.timestamp <= end_timestamp)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def _resolve_density_and_load_type_id(
        self,
        trip: Trip | None,
        explicit_load_type_id: int | None = None,
    ) -> tuple[float | None, int | None]:
        """Определить плотность и load_type_id для пересчёта volume/weight."""
        if explicit_load_type_id is not None:
            density = await self._density_for_load_type_id(explicit_load_type_id)
            return density, explicit_load_type_id
        if trip is None or trip.loading_place_id is None:
            return None, None
        return await self._density_and_load_type_for_place_id(trip.loading_place_id)

    async def update_change_fields_for_trip(
        self,
        db: AsyncSession,
        trip: Trip,
        new_change_volume: float | None = None,
        new_change_weight: float | None = None,
        new_load_type_id: int | None = None,
    ) -> None:
        """Обновить одно из полей (change_volume/change_weight) и пересчитать второе.

        Логика:
        - Находим записи PlaceRemainingHistory по cycle_id рейса.
        - Определяем плотность руды.
        - Если изменили объём — пересчитываем вес.
        - Если изменили вес — пересчитываем объём.
        - Для каждой записи loading/unloading:
          - если запись существует — обновляем volume/weight
          - если записи нет — создаем её на основе данных рейса
        - Пересчитываем остатки на местах погрузки и разгрузки через graph-service.
        """
        if (
            (new_change_volume is None)
            and (new_change_weight is None)
            and (new_load_type_id is None)
        ):
            raise ValueError("Нужно передать change_volume, change_weight или load_type_id")
        if new_change_volume is not None and new_change_weight is not None:
            raise ValueError("Нужно передать только одно поле: change_volume или change_weight")

        cycle_id = trip.cycle_id

        # Находим историю по циклу
        query = select(PlaceRemainingHistory).where(PlaceRemainingHistory.cycle_id == cycle_id)
        result = await db.execute(query)
        history_items: list[PlaceRemainingHistory] = list(result.scalars().all())

        records_by_type: dict[RemainingChangeTypeEnum, PlaceRemainingHistory] = {}
        for item in history_items:
            if item.change_type in (
                RemainingChangeTypeEnum.loading,
                RemainingChangeTypeEnum.unloading,
            ):
                records_by_type[item.change_type] = item

        loading_record = records_by_type.get(RemainingChangeTypeEnum.loading)
        unloading_record = records_by_type.get(RemainingChangeTypeEnum.unloading)

        # Старые значения для логов/аудита: берем из любой существующей записи
        existing_record = loading_record or unloading_record
        old_abs_volume = (
            abs(existing_record.change_volume) if existing_record and existing_record.change_volume is not None else 0.0
        )
        old_abs_weight = (
            abs(existing_record.change_weight) if existing_record and existing_record.change_weight is not None else 0.0
        )

        if new_load_type_id is not None and new_load_type_id <= 0:
            raise ValueError("load_type_id должен быть положительным числом")

        density, load_type_id = await self._resolve_density_and_load_type_id(
            trip=trip,
            explicit_load_type_id=new_load_type_id,
        )
        if density is None:
            raise ValueError("Не удалось определить плотность для пересчета change_volume/change_weight")

        if new_change_volume is not None:
            new_abs_volume = round(abs(new_change_volume), 1)
            new_abs_weight = round(new_abs_volume * density, 3)
            update_field = "change_volume"
        elif new_change_weight is not None:
            if new_change_weight < 0:
                raise ValueError("new_change_weight не может быть отрицательным")
            new_abs_weight = round(abs(new_change_weight), 3)
            new_abs_volume = round(new_abs_weight / density, 1)
            update_field = "change_weight"
        elif existing_record and existing_record.change_volume is not None:
            new_abs_volume = round(abs(existing_record.change_volume), 1)
            new_abs_weight = round(new_abs_volume * density, 3)
            update_field = "load_type_id"
        elif existing_record and existing_record.change_weight is not None:
            new_abs_weight = round(abs(existing_record.change_weight), 3)
            new_abs_volume = round(new_abs_weight / density, 1)
            update_field = "load_type_id"
        else:
            raise ValueError("Для изменения load_type_id в рейсе нужны существующие change_volume или change_weight")

        def _create_record(
            change_type: RemainingChangeTypeEnum,
            place_id: int,
            timestamp: datetime,
            signed_volume: float,
            signed_weight: float,
            record_load_type_id: int | None,
            trip_obj: Trip,
        ) -> PlaceRemainingHistory:
            record = PlaceRemainingHistory(
                id=str(uuid.uuid4()),
                place_id=place_id,
                change_type=change_type,
                change_volume=signed_volume,
                change_weight=signed_weight,
                load_type_id=record_load_type_id,
                timestamp=timestamp,
                cycle_id=cycle_id,
                task_id=trip_obj.task_id,
                shift_id=trip_obj.shift_id,
                vehicle_id=trip_obj.vehicle_id,
                source="dispatcher",
            )
            db.add(record)
            return record

        def _upsert_record(
            *,
            change_type: RemainingChangeTypeEnum,
            existing: PlaceRemainingHistory | None,
            signed_volume: float,
            signed_weight: float,
            record_load_type_id: int | None,
            place_id: int | None,
            timestamp: datetime | None,
        ) -> tuple[PlaceRemainingHistory | None, bool]:
            """Обновить существующую запись или создать новую (если existing is None).

            Возвращает (record | None, created_flag).
            """
            if existing is not None:
                existing.change_volume = signed_volume
                existing.change_weight = signed_weight
                if record_load_type_id is not None:
                    existing.load_type_id = record_load_type_id
                return existing, False

            label = change_type.value
            if not place_id or not timestamp:
                logger.error(
                    f"update_change_fields_for_trip: {label} data not set",
                    cycle_id=cycle_id,
                    **{f"{label}_place_id": place_id, f"{label}_timestamp": timestamp},
                )
                return None, False

            return (
                _create_record(
                    change_type=change_type,
                    place_id=place_id,
                    timestamp=timestamp,
                    signed_volume=signed_volume,
                    signed_weight=signed_weight,
                    record_load_type_id=record_load_type_id,
                    trip_obj=trip,
                ),
                True,
            )

        created_loading = False
        created_unloading = False

        # upsert для loading/unloading (обновить если есть, иначе создать)
        loading_record, created_loading = _upsert_record(
            change_type=RemainingChangeTypeEnum.loading,
            existing=loading_record,
            signed_volume=-new_abs_volume,
            signed_weight=-new_abs_weight,
            record_load_type_id=load_type_id,
            place_id=trip.loading_place_id,
            timestamp=trip.loading_timestamp,
        )
        if loading_record is None:
            return

        unloading_record, created_unloading = _upsert_record(
            change_type=RemainingChangeTypeEnum.unloading,
            existing=unloading_record,
            signed_volume=new_abs_volume,
            signed_weight=new_abs_weight,
            record_load_type_id=load_type_id,
            place_id=trip.unloading_place_id,
            timestamp=trip.unloading_timestamp,
        )
        if unloading_record is None:
            return

        await db.commit()

        # refresh только для созданных (id мы задаем сами, но refresh полезен для единообразия)
        if created_loading:
            await db.refresh(loading_record)
        if created_unloading:
            await db.refresh(unloading_record)

        logger.info(
            "update_change_fields_for_trip: upserted history records",
            cycle_id=cycle_id,
            created_loading=created_loading,
            created_unloading=created_unloading,
            update_field=update_field,
            density=density,
            old_volume=old_abs_volume,
            new_volume=new_abs_volume,
            old_weight=old_abs_weight,
            new_weight=new_abs_weight,
        )

        # Вызываем handle_place_remaining_change для обновления graph-service
        # после модификации записей
        # Обновляем graph-service для места погрузки
        loading_place_remaining_data = {
            "id": loading_record.id,
            "place_id": loading_record.place_id,
            "change_type": loading_record.change_type.value,
            "change_volume": loading_record.change_volume,
            "load_type_id": loading_record.load_type_id,
            "change_weight": loading_record.change_weight,
            "source": loading_record.source,
            "task_id": loading_record.task_id,
            "shift_id": loading_record.shift_id,
            "cycle_id": loading_record.cycle_id,
        }
        loading_context_data = {
            "vehicle_id": loading_record.vehicle_id,
            "cycle_id": loading_record.cycle_id,
            "task_id": loading_record.task_id,
            "shift_id": loading_record.shift_id,
        }
        await handle_place_remaining_change(
            pr_data=loading_place_remaining_data,
            context_data=loading_context_data,
            event_timestamp=loading_record.timestamp,
            db=db,
        )

        # Обновляем graph-service для места разгрузки
        unloading_place_remaining_data = {
            "id": unloading_record.id,
            "place_id": unloading_record.place_id,
            "change_type": unloading_record.change_type.value,
            "change_volume": unloading_record.change_volume,
            "load_type_id": unloading_record.load_type_id,
            "change_weight": unloading_record.change_weight,
            "source": unloading_record.source,
            "task_id": unloading_record.task_id,
            "shift_id": unloading_record.shift_id,
            "cycle_id": unloading_record.cycle_id,
        }
        unloading_context_data = {
            "vehicle_id": unloading_record.vehicle_id,
            "cycle_id": unloading_record.cycle_id,
            "task_id": unloading_record.task_id,
            "shift_id": unloading_record.shift_id,
        }
        await handle_place_remaining_change(
            pr_data=unloading_place_remaining_data,
            context_data=unloading_context_data,
            event_timestamp=unloading_record.timestamp,
            db=db,
        )

        logger.info(
            "update_change_fields_for_trip: place remaining updated via handle_place_remaining_change",
            cycle_id=cycle_id,
            update_field=update_field,
            old_volume=old_abs_volume,
            new_volume=new_abs_volume,
            old_weight=old_abs_weight,
            new_weight=new_abs_weight,
        )

    async def sync_trip_history_for_cycle(
        self,
        db: AsyncSession,
        cycle_id: str,
        new_change_volume: float | None = None,
        new_change_weight: float | None = None,
    ) -> None:
        """Синхронизировать loading/unloading историю рейса.

        Правила:
        - Вес фиксируем всегда (если он известен).
        - Объем фиксируем только когда известна метка места для конкретной операции и есть плотность.
        """
        trip_query = select(Trip).where(Trip.cycle_id == cycle_id)
        trip_result = await db.execute(trip_query)
        trip = trip_result.scalar_one_or_none()
        if trip is None:
            logger.warning("sync_trip_history_for_cycle: trip not found", cycle_id=cycle_id)
            return

        query = (
            select(PlaceRemainingHistory)
            .where(PlaceRemainingHistory.cycle_id == cycle_id)
            .order_by(PlaceRemainingHistory.timestamp)
        )

        result = await db.execute(query)
        history_items: list[PlaceRemainingHistory] = list(result.scalars().all())

        loading_record: PlaceRemainingHistory | None = None
        unloading_record: PlaceRemainingHistory | None = None
        for history_item in history_items:
            if history_item.change_type == RemainingChangeTypeEnum.loading and loading_record is None:
                loading_record = history_item
            elif history_item.change_type == RemainingChangeTypeEnum.unloading and unloading_record is None:
                unloading_record = history_item

        existing_record: PlaceRemainingHistory | None = None
        existing_abs_volume: float | None = None
        existing_abs_weight: float | None = None

        existing_record = loading_record or unloading_record
        if existing_record is not None:
            if existing_record.change_volume is not None:
                existing_abs_volume = abs(existing_record.change_volume)
            if existing_record.change_weight is not None:
                existing_abs_weight = abs(existing_record.change_weight)

        old_places_to_recalculate = {
            pid
            for pid in (
                loading_record.place_id if loading_record else None,
                unloading_record.place_id if unloading_record else None,
            )
            if pid is not None
        }

        density, load_type_id = await self._resolve_density_and_load_type_id(trip=trip)

        weight_value = self._round_change_weight(existing_abs_weight) if existing_abs_weight is not None else None
        volume_value = self._round_change_volume(existing_abs_volume) if existing_abs_volume is not None else None

        # Новые значения имеют приоритет над existing_*.
        if new_change_weight is not None:
            weight_value = self._round_change_weight(new_change_weight)
            if density is not None:
                volume_value = self._round_change_volume(weight_value / density)
        elif new_change_volume is not None:
            volume_value = self._round_change_volume(new_change_volume)
            if density is not None:
                weight_value = self._round_change_weight(volume_value * density)
        elif density is not None:
            if volume_value is None and weight_value is not None:
                volume_value = self._round_change_volume(weight_value / density)
            if weight_value is None and volume_value is not None:
                weight_value = self._round_change_weight(volume_value * density)

        if weight_value is None and volume_value is None:
            logger.info("sync_trip_history_for_cycle: nothing to sync", cycle_id=cycle_id)
            return

        has_defined_place = trip.loading_place_id is not None or trip.unloading_place_id is not None
        if weight_value is None:
            raise ValueError("Не удалось определить change_weight для истории остатков рейса")
        if has_defined_place and volume_value is None:
            raise ValueError(
                "Для рейса с определенным ПП/ПР необходимо передать change_volume "
                "или обеспечить возможность его пересчета по плотности",
            )

        def _upsert(
            *,
            existing_record: PlaceRemainingHistory | None,
            change_type: RemainingChangeTypeEnum,
            place_id: int | None,
            timestamp: datetime | None,
            sign: int,
        ) -> PlaceRemainingHistory | None:
            if timestamp is None:
                return existing_record

            signed_weight = weight_value * sign
            signed_volume = volume_value * sign if (place_id is not None and volume_value is not None) else None

            if existing_record is None:
                record = PlaceRemainingHistory(
                    id=str(uuid.uuid4()),
                    place_id=place_id,
                    change_type=change_type,
                    change_volume=signed_volume,
                    change_weight=signed_weight,
                    load_type_id=load_type_id,
                    timestamp=timestamp,
                    cycle_id=cycle_id,
                    task_id=trip.task_id,
                    shift_id=trip.shift_id,
                    vehicle_id=trip.vehicle_id,
                    source="dispatcher",
                )
                db.add(record)
                return record

            existing_record.place_id = place_id
            existing_record.timestamp = timestamp
            existing_record.change_weight = signed_weight
            existing_record.change_volume = signed_volume
            existing_record.load_type_id = load_type_id
            return existing_record

        loading_record = _upsert(
            existing_record=loading_record,
            change_type=RemainingChangeTypeEnum.loading,
            place_id=trip.loading_place_id,
            timestamp=trip.loading_timestamp,
            sign=-1,
        )
        unloading_record = _upsert(
            existing_record=unloading_record,
            change_type=RemainingChangeTypeEnum.unloading,
            place_id=trip.unloading_place_id,
            timestamp=trip.unloading_timestamp,
            sign=1,
        )

        await db.commit()

        new_places_to_recalculate = {
            pid
            for pid in (
                loading_record.place_id if loading_record else None,
                unloading_record.place_id if unloading_record else None,
            )
            if pid is not None
        }
        for place_id in sorted(old_places_to_recalculate | new_places_to_recalculate):
            await recalculate_and_update_place_stock(place_id=place_id, db=db)

    async def delete_by_cycle_id(
        self,
        db: AsyncSession,
        cycle_id: str,
    ) -> None:
        """Удалить записи об остатках по cycle_id и пересчитать остатки для затронутых мест.

        Логика:
        - Находит записи PlaceRemainingHistory по cycle_id.
        - Получает уникальные place_id из этих записей.
        - Удаляет записи по cycle_id.
        - Для каждого place_id пересчитывает остатки через обновление graph-service.

        Args:
            db: Database session
            cycle_id: ID цикла/рейса
        """
        # Находим записи по циклу перед удалением
        query = select(PlaceRemainingHistory).where(PlaceRemainingHistory.cycle_id == cycle_id)
        result = await db.execute(query)
        records_to_delete: list[PlaceRemainingHistory] = list(result.scalars().all())

        if not records_to_delete:
            logger.warning(
                "delete_by_cycle_id: no records found for cycle_id",
                cycle_id=cycle_id,
            )
            return

        # Получаем уникальные place_id из записей, которые будут удалены
        affected_place_ids = set()
        for record in records_to_delete:
            if record.place_id is not None:
                affected_place_ids.add(record.place_id)

        # Удаляем записи по cycle_id
        delete_query = delete(PlaceRemainingHistory).where(PlaceRemainingHistory.cycle_id == cycle_id)
        await db.execute(delete_query)
        await db.commit()

        logger.info(
            "delete_by_cycle_id: records deleted",
            cycle_id=cycle_id,
            deleted_count=len(records_to_delete),
            affected_place_ids=list(affected_place_ids),
        )

        # Пересчитываем остатки для каждого затронутого места
        for place_id in affected_place_ids:
            try:
                await recalculate_and_update_place_stock(place_id=place_id, db=db)
                logger.info(
                    "delete_by_cycle_id: place stock recalculated",
                    cycle_id=cycle_id,
                    place_id=place_id,
                )
            except Exception as e:
                logger.error(
                    "delete_by_cycle_id: failed to recalculate stock for place",
                    cycle_id=cycle_id,
                    place_id=place_id,
                    error=str(e),
                    exc_info=True,
                )
                # Продолжаем обработку других мест даже если одно не удалось


place_remaining_service = PlaceRemainingService()
