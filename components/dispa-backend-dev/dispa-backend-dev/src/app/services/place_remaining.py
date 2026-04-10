"""Сервис для работы с остатками на местах."""

import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PlaceRemainingHistoryCreate
from app.database.models import PlaceRemainingHistory, Trip
from app.enums import RemainingChangeTypeEnum
from app.services.event_handlers import handle_place_remaining_change
from app.services.place_info import recalculate_and_update_place_stock


class PlaceRemainingService:
    """Сервис управления историей остатков на местах."""

    async def create_history(
        self,
        db: AsyncSession,
        data: PlaceRemainingHistoryCreate,
        notify_graph: bool = True,
    ) -> PlaceRemainingHistory:
        """Создать запись истории и опционально уведомить graph-service."""
        if data.change_amount is None:
            raise ValueError("change_amount is required (or provide target_stock for manual correction)")

        history_id = str(uuid.uuid4())

        history = PlaceRemainingHistory(
            id=history_id,
            place_id=data.place_id,
            change_type=data.change_type,
            change_amount=round(float(data.change_amount), 1),
            timestamp=data.timestamp,
            cycle_id=data.cycle_id,
            task_id=data.task_id,
            shift_id=data.shift_id,
            vehicle_id=data.vehicle_id,
            source=data.source,
        )

        db.add(history)
        await db.commit()
        await db.refresh(history)

        # Вызываем handle_place_remaining_change для обновления graph-service
        # после создания записи (если требуется уведомление graph-service)
        if notify_graph:
            place_remaining_data = {
                "id": history.id,
                "place_id": history.place_id,
                "change_type": history.change_type.value,
                "change_amount": history.change_amount,
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

        return history

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

    async def update_change_amount_for_trip(
        self,
        db: AsyncSession,
        cycle_id: str,
        new_change_amount: float,
    ) -> None:
        """Обновить change_amount (вес/объем) для завершенного рейса и пересчитать остатки.

        Логика:
        - Находим записи PlaceRemainingHistory по cycle_id.
        - Для каждой из записей (loading/unloading):
          - если запись существует — обновляем change_amount на новое значение
          - если записи нет — создаем ее на основе данных рейса с новым change_amount
        - Пересчитываем остатки на местах погрузки и разгрузки через graph-service.
        """
        if new_change_amount is None:
            return

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

        new_abs_amount = round(abs(new_change_amount), 1)

        # Старое значение для логов/аудита: берем из любой существующей записи
        existing_record = loading_record or unloading_record
        old_abs_amount = abs(existing_record.change_amount) if existing_record else 0.0

        need_trip = loading_record is None or unloading_record is None
        trip: Trip | None = None
        if need_trip:
            trip_query = select(Trip).where(Trip.cycle_id == cycle_id)
            trip_result = await db.execute(trip_query)
            trip = trip_result.scalar_one_or_none()

            if not trip:
                logger.error(
                    "update_change_amount_for_trip: trip not found",
                    cycle_id=cycle_id,
                )
                return

        def _create_record(
            change_type: RemainingChangeTypeEnum,
            place_id: int,
            timestamp: datetime,
            signed_amount: float,
            trip_obj: Trip,
        ) -> PlaceRemainingHistory:
            record = PlaceRemainingHistory(
                id=str(uuid.uuid4()),
                place_id=place_id,
                change_type=change_type,
                change_amount=signed_amount,
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
            signed_amount: float,
            place_id: int | None,
            timestamp: datetime | None,
        ) -> tuple[PlaceRemainingHistory | None, bool]:
            """Обновить существующую запись или создать новую (если existing is None).

            Возвращает (record | None, created_flag).
            """
            if existing is not None:
                existing.change_amount = signed_amount
                return existing, False

            if trip is None:
                return None, False
            label = change_type.value
            if not place_id or not timestamp:
                logger.error(
                    f"update_change_amount_for_trip: {label} data not set",
                    cycle_id=cycle_id,
                    **{f"{label}_place_id": place_id, f"{label}_timestamp": timestamp},
                )
                return None, False

            return (
                _create_record(
                    change_type=change_type,
                    place_id=place_id,
                    timestamp=timestamp,
                    signed_amount=signed_amount,
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
            signed_amount=-new_abs_amount,
            place_id=getattr(trip, "loading_place_id", None),
            timestamp=getattr(trip, "loading_timestamp", None),
        )
        if loading_record is None:
            return

        unloading_record, created_unloading = _upsert_record(
            change_type=RemainingChangeTypeEnum.unloading,
            existing=unloading_record,
            signed_amount=new_abs_amount,
            place_id=getattr(trip, "unloading_place_id", None),
            timestamp=getattr(trip, "unloading_timestamp", None),
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
            "update_change_amount_for_trip: upserted history records",
            cycle_id=cycle_id,
            created_loading=created_loading,
            created_unloading=created_unloading,
            old_amount=old_abs_amount,
            new_amount=new_abs_amount,
        )

        # Вызываем handle_place_remaining_change для обновления graph-service
        # после модификации записей
        # Обновляем graph-service для места погрузки
        loading_place_remaining_data = {
            "id": loading_record.id,
            "place_id": loading_record.place_id,
            "change_type": loading_record.change_type.value,
            "change_amount": loading_record.change_amount,
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
            "change_amount": unloading_record.change_amount,
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
            "update_change_amount_for_trip: place remaining updated via handle_place_remaining_change",
            cycle_id=cycle_id,
            old_amount=old_abs_amount,
            new_amount=new_abs_amount,
        )

    async def update_places_for_trip(
        self,
        db: AsyncSession,
        cycle_id: str,
        old_loading_place_id: int | None,
        new_loading_place_id: int | None,
        old_unloading_place_id: int | None,
        new_unloading_place_id: int | None,
    ) -> None:
        """Обновить места погрузки/разгрузки в записях PlaceRemainingHistory для рейса.

        Логика:
        1. Ищем записи PlaceRemainingHistory по cycle_id для старого места
        2. Меняем place_id в найденных записях на новое место
        3. Запускаем пересчет остатков - он увидит что у одного места пропала запись,
           а у другого появилась

        Args:
            db: Database session
            cycle_id: ID цикла/рейса
            old_loading_place_id: Старое место погрузки (None если не менялось)
            new_loading_place_id: Новое место погрузки (None если не менялось)
            old_unloading_place_id: Старое место разгрузки (None если не менялось)
            new_unloading_place_id: Новое место разгрузки (None если не менялось)
        """
        # Находим историю по циклу
        query = (
            select(PlaceRemainingHistory)
            .where(PlaceRemainingHistory.cycle_id == cycle_id)
            .order_by(PlaceRemainingHistory.timestamp)
        )
        result = await db.execute(query)
        history_items: list[PlaceRemainingHistory] = list(result.scalars().all())

        if not history_items:
            logger.warning(
                "update_places_for_trip: no PlaceRemainingHistory records found",
                cycle_id=cycle_id,
            )
            return

        loading_record: PlaceRemainingHistory | None = None
        unloading_record: PlaceRemainingHistory | None = None

        for history_item in history_items:
            if history_item.change_type == RemainingChangeTypeEnum.loading:
                loading_record = history_item
            elif history_item.change_type == RemainingChangeTypeEnum.unloading:
                unloading_record = history_item

        try:
            # Собираем места, которые нужно обновить в graph-service
            places_to_recalculate = set()

            # Обработка изменения места погрузки
            if (
                old_loading_place_id is not None
                and new_loading_place_id is not None
                and old_loading_place_id != new_loading_place_id
            ):
                if not loading_record:
                    logger.warning(
                        "update_places_for_trip: loading record not found",
                        cycle_id=cycle_id,
                    )
                else:
                    # Проверяем, что запись действительно относится к старому месту
                    if loading_record.place_id == old_loading_place_id:
                        # Меняем place_id в существующей записи на новое место
                        loading_record.place_id = new_loading_place_id

                        places_to_recalculate.add(old_loading_place_id)
                        places_to_recalculate.add(new_loading_place_id)

                        logger.info(
                            "update_places_for_trip: loading place updated",
                            cycle_id=cycle_id,
                            old_place_id=old_loading_place_id,
                            new_place_id=new_loading_place_id,
                        )
                    else:
                        logger.warning(
                            "update_places_for_trip: loading record place_id mismatch",
                            cycle_id=cycle_id,
                            expected_place_id=old_loading_place_id,
                            actual_place_id=loading_record.place_id,
                        )

            # Обработка изменения места разгрузки
            if (
                old_unloading_place_id is not None
                and new_unloading_place_id is not None
                and old_unloading_place_id != new_unloading_place_id
            ):
                if not unloading_record:
                    logger.warning(
                        "update_places_for_trip: unloading record not found",
                        cycle_id=cycle_id,
                    )
                else:
                    # Проверяем, что запись действительно относится к старому месту
                    if unloading_record.place_id == old_unloading_place_id:
                        # Меняем place_id в существующей записи на новое место
                        unloading_record.place_id = new_unloading_place_id

                        places_to_recalculate.add(old_unloading_place_id)
                        places_to_recalculate.add(new_unloading_place_id)

                        logger.info(
                            "update_places_for_trip: unloading place updated",
                            cycle_id=cycle_id,
                            old_place_id=old_unloading_place_id,
                            new_place_id=new_unloading_place_id,
                        )
                    else:
                        logger.warning(
                            "update_places_for_trip: unloading record place_id mismatch",
                            cycle_id=cycle_id,
                            expected_place_id=old_unloading_place_id,
                            actual_place_id=unloading_record.place_id,
                        )

            # Если были изменения, коммитим их
            if places_to_recalculate:
                await db.commit()

                # Пересчитываем остатки для всех затронутых мест
                # Пересчет увидит что у одного места пропала запись, а у другого появилась
                for place_id in places_to_recalculate:
                    await recalculate_and_update_place_stock(place_id=place_id, db=db)

                logger.info(
                    "update_places_for_trip: place remaining history updated successfully",
                    cycle_id=cycle_id,
                    recalculated_places=list(places_to_recalculate),
                )
            else:
                logger.info(
                    "update_places_for_trip: no changes to apply",
                    cycle_id=cycle_id,
                )
        except Exception as e:
            logger.error(
                "update_places_for_trip: failed to update places",
                cycle_id=cycle_id,
                error=str(e),
                exc_info=True,
            )
            raise

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
