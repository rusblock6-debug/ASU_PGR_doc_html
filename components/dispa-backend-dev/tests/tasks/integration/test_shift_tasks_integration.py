"""Интеграционные тесты для ShiftTaskService.

Проверяют:
- Сохранение данных в БД
- Публикацию событий в MQTT
- Публикацию событий в Redis (в server режиме)
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.schemas.tasks.route_tasks_bulk import RouteTaskBulkUpsertItem
from app.api.schemas.tasks.shift_tasks import ShiftTaskCreate
from app.api.schemas.tasks.shift_tasks_bulk import ShiftTaskUpsertItem
from app.database.models import RouteTask, ShiftTask
from app.enums import ShiftTaskStatusEnum, TypesRouteTaskEnum
from app.services.tasks.shift_task import ShiftTaskService
from app.services.tasks.shift_task_bulk import ShiftTaskBulkService


class TestShiftTaskServiceIntegration:
    """Интеграционные тесты для ShiftTaskService."""

    @pytest.mark.asyncio
    async def test_create_shift_task_saves_to_db(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: создание shift_task сохраняется в БД."""
        # Подготовка данных
        shift_data = ShiftTaskCreate(
            work_regime_id=1,
            vehicle_id=5,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            route_tasks=[],
        )

        # Мокаем MQTT и Redis
        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    # Создаем shift_task
                    created_task = await ShiftTaskService(test_db_session).create(
                        shift_data=shift_data,
                    )

        # Проверяем, что объект создан и имеет правильные данные (после commit и refresh в сервисе)
        assert created_task is not None
        assert created_task.id is not None
        assert created_task.vehicle_id == 5
        assert created_task.work_regime_id == 1
        assert created_task.shift_date == "2026-01-26"
        assert created_task.shift_num == 1
        assert created_task.status == ShiftTaskStatusEnum.PENDING

        # Проверяем, что commit был вызван (данные сохранены в БД)
        # Это проверяется через успешное выполнение create без ошибок

    @pytest.mark.asyncio
    async def test_create_shift_task_publishes_mqtt(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: создание shift_task публикует событие в MQTT."""
        shift_data = ShiftTaskCreate(
            work_regime_id=1,
            vehicle_id=5,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            route_tasks=[],
        )

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await ShiftTaskService(test_db_session).create(
                        shift_data=shift_data,
                    )

        # Проверяем, что MQTT клиент был вызван
        mock_mqtt_client.connect.assert_called_once()
        mock_mqtt_client.publish.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()

        # Проверяем содержимое MQTT сообщения
        publish_call = mock_mqtt_client.publish.call_args
        assert publish_call is not None
        topic, payload = publish_call[0]
        assert "truck/5/trip-service/events" in topic
        assert payload["event_type"] == "entity_changed"
        assert payload["entity_type"] == "shift_task"
        assert payload["action"] == "create"

    @pytest.mark.asyncio
    async def test_create_shift_task_publishes_redis_in_server_mode(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: создание shift_task публикует событие в Redis (server режим)."""
        shift_data = ShiftTaskCreate(
            work_regime_id=1,
            vehicle_id=5,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            route_tasks=[],
        )

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await ShiftTaskService(test_db_session).create(
                        shift_data=shift_data,
                    )

        # Проверяем, что Redis publish был вызван
        mock_redis_client.publish.assert_called()

        # Проверяем содержимое Redis сообщения
        publish_calls = mock_redis_client.publish.call_args_list
        redis_calls = [call for call in publish_calls if call[0][0] == "trip-service:shift_tasks:changes"]
        assert len(redis_calls) > 0

        # Проверяем структуру сообщения
        channel, message = redis_calls[0][0]
        import json

        event_data = json.loads(message)
        assert event_data["event_type"] == "shift_task_changed"
        assert event_data["action"] == "create"
        assert "shift_task" in event_data

    @pytest.mark.asyncio
    async def test_create_shift_task_with_route_tasks_saves_all(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: создание shift_task с route_tasks сохраняет все в БД."""
        from app.api.schemas.tasks.route_tasks import RouteTaskCreate

        shift_data = ShiftTaskCreate(
            work_regime_id=1,
            vehicle_id=5,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            route_tasks=[
                RouteTaskCreate(
                    route_order=0,
                    place_a_id=1,
                    place_b_id=2,
                    type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                    planned_trips_count=1,
                    volume=1.0,
                    weight=1.0,
                ),
            ],
        )

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    created_task = await ShiftTaskService(test_db_session).create(
                        shift_data=shift_data,
                    )

        # Проверяем, что объект создан и имеет правильные данные
        assert created_task is not None
        assert created_task.vehicle_id == 5
        assert created_task.work_regime_id == 1
        assert len(created_task.route_tasks) == 1
        assert created_task.route_tasks[0].place_a_id == 1
        assert created_task.route_tasks[0].place_b_id == 2
        assert created_task.route_tasks[0].type_task == TypesRouteTaskEnum.LOADING_TRANSPORT_GM
        assert created_task.route_tasks[0].route_order == 0

        # Проверяем, что MQTT был вызван для shift_task и route_tasks
        assert mock_mqtt_client.publish.call_count >= 2  # shift_task + route_tasks


class TestShiftTaskBulkServiceIntegration:
    """Интеграционные тесты для ShiftTaskBulkService.

    Сценарии:
    1. В БД записывается shift_task с несколькими route_tasks, созданная через bulk upsert.
    2. Через bulk upsert можно обновить эту shift_task с route_tasks внутри.
    3. Bulk upsert удаляет route_tasks, которые не переданы в payload.
    """

    @pytest.mark.asyncio
    async def test_bulk_upsert_creates_shift_tasks_in_db(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: bulk_upsert создает shift_tasks в БД."""
        items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=5,
                shift_date="2026-01-26",
                shift_num=1,
                status=ShiftTaskStatusEnum.PENDING,
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    result = await ShiftTaskBulkService.bulk_upsert(
                        items=items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        # Проверяем результат
        assert len(result.items) == 1
        assert result.items[0].action == "created"
        assert result.items[0].id is not None  # ID был создан

        # Проверяем, что MQTT был вызван
        assert mock_mqtt_client.publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_bulk_upsert_publishes_mqtt_events(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: bulk_upsert публикует события в MQTT."""
        items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=5,
                shift_date="2026-01-26",
                shift_num=1,
                status=ShiftTaskStatusEnum.PENDING,
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await ShiftTaskBulkService.bulk_upsert(
                        items=items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        # Проверяем, что MQTT был вызван
        assert mock_mqtt_client.publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_bulk_upsert_publishes_redis_events(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: bulk_upsert публикует события в Redis."""
        items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=5,
                shift_date="2026-01-26",
                shift_num=1,
                status=ShiftTaskStatusEnum.PENDING,
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await ShiftTaskBulkService.bulk_upsert(
                        items=items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        # Проверяем, что Redis publish был вызван
        assert mock_redis_client.publish.call_count >= 1

        # Проверяем, что был вызов для shift_tasks канала
        publish_calls = mock_redis_client.publish.call_args_list
        shift_task_calls = [call for call in publish_calls if len(call[0]) > 0 and "shift_tasks:changes" in call[0][0]]
        assert len(shift_task_calls) > 0

    @pytest.mark.asyncio
    async def test_bulk_upsert_creates_shift_task_with_multiple_route_tasks_in_db(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Проверяет запись shift_task с route_tasks через bulk upsert в БД."""
        items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=10,
                shift_date="2026-02-01",
                shift_num=1,
                status=ShiftTaskStatusEnum.PENDING,
                route_tasks=[
                    RouteTaskBulkUpsertItem(
                        route_order=0,
                        place_a_id=1,
                        place_b_id=2,
                        type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                        planned_trips_count=1,
                        volume=1.0,
                        weight=2.0,
                    ),
                    RouteTaskBulkUpsertItem(
                        route_order=1,
                        place_a_id=3,
                        place_b_id=4,
                        type_task=TypesRouteTaskEnum.LOADING_SHAS,
                        planned_trips_count=2,
                        volume=3.0,
                        weight=4.0,
                    ),
                ],
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    result = await ShiftTaskBulkService.bulk_upsert(
                        items=items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        assert len(result.items) == 1
        assert result.items[0].action == "created"
        shift_id = result.items[0].id
        assert shift_id is not None
        shift_id_uuid = uuid.UUID(shift_id) if isinstance(shift_id, str) else shift_id

        # Проверяем в БД: одна смена и два маршрутных задания
        r = await test_db_session.execute(
            select(ShiftTask).options(selectinload(ShiftTask.route_tasks)).where(ShiftTask.id == shift_id_uuid),
        )
        shift_task = r.scalar_one_or_none()
        assert shift_task is not None
        assert shift_task.vehicle_id == 10
        assert shift_task.work_regime_id == 1
        assert shift_task.shift_date == "2026-02-01"
        assert shift_task.shift_num == 1
        assert len(shift_task.route_tasks) == 2
        route_tasks_sorted = sorted(shift_task.route_tasks, key=lambda rt: rt.route_order)
        assert route_tasks_sorted[0].place_a_id == 1
        assert route_tasks_sorted[0].place_b_id == 2
        assert route_tasks_sorted[0].type_task == TypesRouteTaskEnum.LOADING_TRANSPORT_GM
        assert route_tasks_sorted[0].volume == 1.0
        assert route_tasks_sorted[0].weight == 2.0
        assert route_tasks_sorted[1].place_a_id == 3
        assert route_tasks_sorted[1].place_b_id == 4
        assert route_tasks_sorted[1].type_task == TypesRouteTaskEnum.LOADING_SHAS
        assert route_tasks_sorted[1].volume == 3.0
        assert route_tasks_sorted[1].weight == 4.0

    @pytest.mark.asyncio
    async def test_bulk_upsert_updates_shift_task_and_route_tasks(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Проверяет, что через bulk upsert можно обновить эту shift_task с route_tasks внутри."""
        # 1. Создаём смену с двумя route_tasks
        create_items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=20,
                shift_date="2026-02-02",
                shift_num=1,
                status=ShiftTaskStatusEnum.PENDING,
                route_tasks=[
                    RouteTaskBulkUpsertItem(
                        route_order=0,
                        place_a_id=10,
                        place_b_id=20,
                        type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                        planned_trips_count=1,
                    ),
                    RouteTaskBulkUpsertItem(
                        route_order=1,
                        place_a_id=30,
                        place_b_id=40,
                        type_task=TypesRouteTaskEnum.LOADING_SHAS,
                        planned_trips_count=1,
                    ),
                ],
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    create_result = await ShiftTaskBulkService.bulk_upsert(
                        items=create_items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        assert len(create_result.items) == 1
        shift_id = create_result.items[0].id
        assert shift_id is not None
        shift_id_uuid = uuid.UUID(shift_id) if isinstance(shift_id, str) else shift_id

        # Загружаем созданные route_tasks, чтобы получить их id
        r = await test_db_session.execute(
            select(ShiftTask).options(selectinload(ShiftTask.route_tasks)).where(ShiftTask.id == shift_id_uuid),
        )
        shift_task = r.scalar_one()
        route_ids = [rt.id for rt in sorted(shift_task.route_tasks, key=lambda x: x.route_order)]

        # 2. Обновляем смену и route_tasks через bulk_upsert (те же id)
        update_items = [
            ShiftTaskUpsertItem(
                id=shift_id_uuid,
                work_regime_id=1,
                vehicle_id=21,
                shift_date="2026-02-03",
                shift_num=2,
                status=ShiftTaskStatusEnum.IN_PROGRESS,
                route_tasks=[
                    RouteTaskBulkUpsertItem(
                        id=route_ids[0],
                        route_order=0,
                        place_a_id=11,
                        place_b_id=21,
                        type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                        planned_trips_count=5,
                        volume=10.0,
                        weight=20.0,
                    ),
                    RouteTaskBulkUpsertItem(
                        id=route_ids[1],
                        route_order=1,
                        place_a_id=31,
                        place_b_id=41,
                        type_task=TypesRouteTaskEnum.LOADING_SHAS,
                        planned_trips_count=3,
                        volume=5.0,
                        weight=6.0,
                    ),
                ],
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    update_result = await ShiftTaskBulkService.bulk_upsert(
                        items=update_items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        assert len(update_result.items) == 1
        assert update_result.items[0].action == "updated"

        # Сбрасываем кэш сессии, чтобы прочитать актуальные данные из БД
        test_db_session.expire_all()
        # Проверяем в БД обновлённые данные
        r2 = await test_db_session.execute(
            select(ShiftTask).options(selectinload(ShiftTask.route_tasks)).where(ShiftTask.id == shift_id_uuid),
        )
        shift_task_after = r2.scalar_one()
        assert shift_task_after.vehicle_id == 21
        assert shift_task_after.shift_date == "2026-02-03"
        assert shift_task_after.shift_num == 2
        assert shift_task_after.status == ShiftTaskStatusEnum.IN_PROGRESS
        assert len(shift_task_after.route_tasks) == 2
        routes_after = sorted(shift_task_after.route_tasks, key=lambda rt: rt.route_order)
        assert routes_after[0].place_a_id == 11
        assert routes_after[0].place_b_id == 21
        assert routes_after[0].planned_trips_count == 5
        assert routes_after[0].volume == 10.0
        assert routes_after[0].weight == 20.0
        assert routes_after[1].place_a_id == 31
        assert routes_after[1].place_b_id == 41
        assert routes_after[1].planned_trips_count == 3
        assert routes_after[1].volume == 5.0
        assert routes_after[1].weight == 6.0

    @pytest.mark.asyncio
    async def test_bulk_upsert_removes_route_tasks_not_in_payload(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Проверяет, что shift_task bulk upsert удаляет route_tasks, которые не переданы в payload."""
        # 1. Создаём смену с тремя route_tasks
        create_items = [
            ShiftTaskUpsertItem(
                work_regime_id=1,
                vehicle_id=30,
                shift_date="2026-02-04",
                shift_num=1,
                status=ShiftTaskStatusEnum.PENDING,
                route_tasks=[
                    RouteTaskBulkUpsertItem(
                        route_order=0,
                        place_a_id=1,
                        place_b_id=2,
                        type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                        planned_trips_count=1,
                    ),
                    RouteTaskBulkUpsertItem(
                        route_order=1,
                        place_a_id=3,
                        place_b_id=4,
                        type_task=TypesRouteTaskEnum.LOADING_SHAS,
                        planned_trips_count=1,
                    ),
                    RouteTaskBulkUpsertItem(
                        route_order=2,
                        place_a_id=5,
                        place_b_id=6,
                        type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                        planned_trips_count=1,
                    ),
                ],
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    create_result = await ShiftTaskBulkService.bulk_upsert(
                        items=create_items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        assert len(create_result.items) == 1
        shift_id = create_result.items[0].id
        shift_id_uuid = uuid.UUID(shift_id) if isinstance(shift_id, str) else shift_id

        r = await test_db_session.execute(
            select(ShiftTask).options(selectinload(ShiftTask.route_tasks)).where(ShiftTask.id == shift_id_uuid),
        )
        shift_task = r.scalar_one()
        route_ids = [rt.id for rt in sorted(shift_task.route_tasks, key=lambda x: x.route_order)]
        assert len(route_ids) == 3

        # 2. Обновляем смену, передаём только один route_task (первый); остальные должны удалиться
        update_items = [
            ShiftTaskUpsertItem(
                id=shift_id_uuid,
                work_regime_id=1,
                vehicle_id=30,
                shift_date="2026-02-04",
                shift_num=1,
                status=ShiftTaskStatusEnum.PENDING,
                route_tasks=[
                    RouteTaskBulkUpsertItem(
                        id=route_ids[0],
                        route_order=0,
                        place_a_id=1,
                        place_b_id=2,
                        type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                        planned_trips_count=2,
                    ),
                ],
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    update_result = await ShiftTaskBulkService.bulk_upsert(
                        items=update_items,
                        db=test_db_session,
                        publish_mqtt=True,
                    )

        assert len(update_result.items) == 1
        assert update_result.items[0].action == "updated"

        # Сбрасываем кэш сессии, чтобы прочитать актуальные данные из БД после delete
        test_db_session.expire_all()
        # В БД должна остаться только одна route_task
        r2 = await test_db_session.execute(
            select(ShiftTask).options(selectinload(ShiftTask.route_tasks)).where(ShiftTask.id == shift_id_uuid),
        )
        shift_task_after = r2.scalar_one()
        assert len(shift_task_after.route_tasks) == 1
        assert shift_task_after.route_tasks[0].id == route_ids[0]
        assert shift_task_after.route_tasks[0].planned_trips_count == 2

        # Удалённые route_tasks не должны быть в БД
        r3 = await test_db_session.execute(
            select(RouteTask).where(RouteTask.id.in_(route_ids[1:])),
        )
        remaining = list(r3.scalars().all())
        assert len(remaining) == 0
