"""Сервис для работы с RouteTask.

Содержит бизнес-логику для отдельных операций с route_tasks:
- Создание отдельного route_task
- Обновление отдельного route_task
- Получение route_task по ID
- Активация route_task
- Удаление route_task
- Список route_tasks с пагинацией
- MQTT публикация
"""

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.exceptions import RouteTaskNotFoundException, ServerErrorException, ShiftTaskNotFoundException
from app.api.exceptions.base import BaseResponseException
from app.api.schemas.tasks.route_tasks import (
    RouteTaskCreate,
    RouteTaskUpdate,
)
from app.database.models import RouteTask, ShiftTask
from app.enums.route_tasks import TripStatusRouteEnum
from app.services.route_summary import _get_current_shift_info
from app.services.tasks.task_manager import cancel_task, set_active_task


class RouteTaskService:
    """Сервис для бизнес-логики RouteTask."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def normalize_status_for_creation(status: TripStatusRouteEnum | None) -> TripStatusRouteEnum:
        """Нормализует статус при создании нового route_task.

        При создании: если статус не задан или EMPTY — выставляем SENT.

        Args:
            status: Исходный статус.

        Returns:
            TripStatusRouteEnum: Нормализованный статус.
        """
        if status is None:
            return TripStatusRouteEnum.SENT
        if status == TripStatusRouteEnum.EMPTY:
            return TripStatusRouteEnum.SENT
        return status

    async def create(
        self,
        route_data: RouteTaskCreate,
    ) -> RouteTask:
        """Создать ОДИНОЧНЫЙ route_task."""
        try:
            payload = route_data.model_dump(exclude_unset=True)
            task_id = payload.pop("id", None)
            vehicle_id = payload.pop("vehicle_id", None)

            shift_task_id = payload.get("shift_task_id")
            shift_task: ShiftTask | None

            if shift_task_id:
                shift_task = await self.session.get(ShiftTask, shift_task_id)
                if not shift_task:
                    raise ShiftTaskNotFoundException(str(shift_task_id))
            else:
                if vehicle_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="vehicle_id is required when shift_task_id is not provided",
                    )

                shift_info = await _get_current_shift_info()
                if not shift_info:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Current shift not determined",
                    )
                shift_date = str(shift_info.get("shift_date") or "")
                shift_num_raw = shift_info.get("shift_num")
                shift_num = int(shift_num_raw) if shift_num_raw is not None else 0
                if not shift_date or shift_num <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Current shift not determined",
                    )

                work_regime_raw = shift_info.get("work_regime_id") or shift_info.get("work_regime") or 1
                try:
                    work_regime_id = int(work_regime_raw)
                except (TypeError, ValueError):
                    work_regime_id = 1

                existing_shift = await self.session.scalar(
                    select(ShiftTask).where(
                        ShiftTask.vehicle_id == int(vehicle_id),
                        ShiftTask.shift_date == shift_date,
                        ShiftTask.shift_num == shift_num,
                    ),
                )
                if existing_shift is not None:
                    shift_task = existing_shift
                else:
                    shift_task = ShiftTask(
                        work_regime_id=work_regime_id,
                        vehicle_id=int(vehicle_id),
                        shift_date=shift_date,
                        shift_num=shift_num,
                    )
                    self.session.add(shift_task)
                    await self.session.flush()

                payload["shift_task_id"] = shift_task.id

            # route_order: если не передан — max+1 в рамках shift_task, иначе 1
            route_order = payload.get("route_order")
            if route_order is None:
                max_order = await self.session.scalar(
                    select(func.max(RouteTask.route_order)).where(RouteTask.shift_task_id == shift_task.id),
                )
                payload["route_order"] = int(max_order or 0) + 1

            # При создании: если статус SENT или EMPTY, меняем на DELIVERED
            payload["status"] = RouteTaskService.normalize_status_for_creation(payload.get("status"))

            if task_id is not None:
                payload["id"] = task_id

            route_task = RouteTask(**payload)
            self.session.add(route_task)

            await self.session.commit()
            await self.session.refresh(route_task)
            logger.info("RouteTask created", route_id=route_task.id, shift_task_id=route_task.shift_task_id)

            return route_task

        except Exception as e:
            await self.session.rollback()
            logger.error("RouteTask create failed", error=str(e), exc_info=True)
            raise ServerErrorException(f"Create failed: {str(e)}") from e

    async def update(self, route_id: str, route_data: RouteTaskUpdate) -> RouteTask:
        """Обновить ОДИНОЧНЫЙ route_task.

        Args:
            route_id: ID route_task
            route_data: Данные для обновления
            db: Database session

        Returns:
            RouteTask: Обновленный route_task

        Raises:
            HTTPException(404): Если route_task не найден
        """
        try:
            route_task = await self.get_with_shift_by_id(route_id=route_id)

            # Применить обновления (только непустые поля)
            update_data = route_data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                setattr(route_task, field, value)

            # ЯВНЫЙ COMMIT
            await self.session.commit()
            await self.session.refresh(route_task)
            logger.info("RouteTask updated", route_id=route_id)

            return route_task

        except HTTPException:
            raise
        except BaseResponseException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error("RouteTask update failed", route_id=route_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}") from e

    async def get_by_id(self, route_id: str) -> RouteTask:
        """Получить route_task по ID.

        Args:
            route_id: ID route_task
            db: Database session

        Returns:
            RouteTask: Найденный route_task

        Raises:
            HTTPException(404): Если route_task не найден
        """
        route_task = await self.session.scalar(select(RouteTask).where(RouteTask.id == route_id))
        if not route_task:
            raise RouteTaskNotFoundException(route_id)
        return route_task

    async def get_with_shift_by_id(self, route_id: str) -> RouteTask:
        """Получить route_task с загруженной shift_id по ID.

        Args:
            route_id: ID route_task
            db: Database session

        Returns:
            RouteTask: Найденный route_task

        Raises:
            HTTPException(404): Если route_task не найден
        """
        route_smtp = select(RouteTask).options(joinedload(RouteTask.shift_task)).where(RouteTask.id == route_id)
        route_task = await self.session.scalar(route_smtp)
        if not route_task:
            raise RouteTaskNotFoundException(route_id)
        return route_task

    async def activate(self, route_id: str, vehicle_id: str) -> RouteTask:
        """Активировать route_task.

        ВАЖНО: Автоматически приостанавливает предыдущее активное задание!
        Не может быть больше одного активного задания одновременно.

        Args:
            route_id: ID route_task
            vehicle_id: ID транспортного средства
            db: Database session

        Returns:
            RouteTask: Активированный route_task

        Raises:
            HTTPException(404): Если route_task не найден
        """
        # Получить задание
        route_task = await self.get_with_shift_by_id(route_id=route_id)
        if not route_task:
            raise RouteTaskNotFoundException(route_id)

        # Активировать задание (автоматически приостановит предыдущее)
        activation_result = await set_active_task(vehicle_id, route_task, self.session)

        await self.session.refresh(route_task)
        logger.info(
            "RouteTask activated",
            route_id=route_id,
            vehicle_id=vehicle_id,
            activation_result=activation_result,
        )
        return route_task

    async def cancel(self, route_id: str, vehicle_id: str) -> RouteTask:
        """Отмена route_task.

        ВАЖНО: При отмене задания если оно было активным автоматически активирует другое

        Args:
            route_id: ID route_task
            vehicle_id: ID транспортного средства
            db: Database session

        Returns:
            RouteTask: Отмененная route_task

        Raises:
            HTTPException(404): Если route_task не найден
        """
        # Получить задание
        route_task = await self.get_with_shift_by_id(route_id=route_id)
        if not route_task:
            raise RouteTaskNotFoundException(route_id)

        # Активировать задание (автоматически приостановит предыдущее)
        activation_result = await cancel_task(vehicle_id, route_task.id, self.session)

        await self.session.refresh(route_task)
        logger.info(
            "[Completed] RouteTask cancel",
            route_id=route_id,
            vehicle_id=vehicle_id,
            activation_result=activation_result,
        )
        return route_task

    async def delete(self, route_id: str) -> None:
        """Удалить route_task."""
        try:
            route_task = await self.get_with_shift_by_id(route_id=route_id)
            if not route_task:
                raise RouteTaskNotFoundException(route_id)
            stmt = delete(RouteTask).where(RouteTask.id == route_id)
            await self.session.execute(stmt)

            await self.session.commit()
            logger.info("RouteTask deleted", route_id=route_id)

        except HTTPException:
            raise
        except BaseResponseException:
            raise
        except Exception as e:
            logger.error("RouteTask delete failed", route_id=route_id, error=str(e), exc_info=True)
            raise ServerErrorException(f"Delete failed: {str(e)}") from e

    # TODO переписать, сделать общую пагинацию
    async def list_paginated(
        self,
        page: int,
        size: int,
        shift_task_id: str | None = None,
        status: TripStatusRouteEnum | None = None,
        vehicle_id: int | None = None,
        place_a_id: int | None = None,
        place_b_id: int | None = None,
    ) -> tuple[list[RouteTask], int]:
        """Получить список route_tasks с пагинацией и фильтрацией.

        Args:
            page: Номер страницы (начиная с 1)
            size: Размер страницы
            shift_task_id: Фильтр по ID смены (опционально)
            status: Фильтр по статусу (опционально)
            vehicle_id: Фильтр по vehicle_id (если shift_task_id не задан — в рамках текущей смены)
            place_a_id: Фильтр по place_a_id (опционально)
            place_b_id: Фильтр по place_b_id (опционально)

        Returns:
            Tuple[List[RouteTask], int]: (список задач, общее количество)
        """
        query = select(RouteTask)

        # TODO Возможна оптимизация, чтобы не тянуть все данные из бд без примененных фильтров
        # Применяем фильтры
        if shift_task_id:
            query = query.where(RouteTask.shift_task_id == shift_task_id)
        if vehicle_id is not None and not shift_task_id:
            shift_info = await _get_current_shift_info()
            if shift_info:
                shift_date = str(shift_info.get("shift_date") or "")
                shift_num_raw = shift_info.get("shift_num")
                shift_num = int(shift_num_raw) if shift_num_raw is not None else 0
                if shift_date and shift_num > 0:
                    query = query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                        ShiftTask.vehicle_id == int(vehicle_id),
                        ShiftTask.shift_date == shift_date,
                        ShiftTask.shift_num == shift_num,
                    )
                else:
                    query = query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                        ShiftTask.vehicle_id == int(vehicle_id),
                    )
            else:
                query = query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                    ShiftTask.vehicle_id == int(vehicle_id),
                )
        if status:
            query = query.where(RouteTask.status == status)
        if place_a_id is not None:
            query = query.where(RouteTask.place_a_id == int(place_a_id))
        if place_b_id is not None:
            query = query.where(RouteTask.place_b_id == int(place_b_id))

        # Подсчет общего количества
        count_query = select(func.count(RouteTask.id)).select_from(RouteTask)
        if shift_task_id:
            count_query = count_query.where(RouteTask.shift_task_id == shift_task_id)
        if vehicle_id is not None and not shift_task_id:
            shift_info = await _get_current_shift_info()
            if shift_info:
                shift_date = str(shift_info.get("shift_date") or "")
                shift_num_raw = shift_info.get("shift_num")
                shift_num = int(shift_num_raw) if shift_num_raw is not None else 0
                if shift_date and shift_num > 0:
                    count_query = count_query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                        ShiftTask.vehicle_id == int(vehicle_id),
                        ShiftTask.shift_date == shift_date,
                        ShiftTask.shift_num == shift_num,
                    )
                else:
                    count_query = count_query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                        ShiftTask.vehicle_id == int(vehicle_id),
                    )
            else:
                count_query = count_query.join(ShiftTask, RouteTask.shift_task_id == ShiftTask.id).where(
                    ShiftTask.vehicle_id == int(vehicle_id),
                )
        if status:
            count_query = count_query.where(RouteTask.status == status)
        if place_a_id is not None:
            count_query = count_query.where(RouteTask.place_a_id == int(place_a_id))
        if place_b_id is not None:
            count_query = count_query.where(RouteTask.place_b_id == int(place_b_id))

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Получение данных с пагинацией и сортировкой
        offset = (page - 1) * size
        query = query.order_by(RouteTask.shift_task_id, RouteTask.route_order).offset(offset).limit(size)

        result = await self.session.execute(query)
        tasks = result.scalars().all()

        # TODO педантик схема для логирования,
        #  с целью собрать схемы всех ответов в одном сесте ?
        logger.info(
            "RouteTasks listed",
            page=page,
            size=size,
            total=total,
            returned=len(tasks),
            shift_task_id=shift_task_id,
            status=status.value if status else None,
        )
        # TODO добавить педантик схему
        return list(tasks), total
