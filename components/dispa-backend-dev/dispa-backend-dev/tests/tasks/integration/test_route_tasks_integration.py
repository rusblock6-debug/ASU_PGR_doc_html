"""Интеграционные тесты для RouteTaskService.

Проверяют:
- Сохранение данных в БД
- Публикацию событий в MQTT
- Публикацию событий в Redis (в server режиме)
"""

from unittest.mock import patch

import pytest

from app.api.schemas.tasks.route_tasks import RouteTaskCreate
from app.api.schemas.tasks.route_tasks_bulk import RouteTaskBulkUpsertItem
from app.database.models import ShiftTask
from app.enums import ShiftTaskStatusEnum, TypesRouteTaskEnum
from app.services.tasks.route_task import RouteTaskService
from app.services.tasks.route_task_bulk import RouteTaskBulkService


class TestRouteTaskServiceIntegration:
    """Интеграционные тесты для RouteTaskService."""

    async def _create_test_shift_task(self, db_session):
        """Вспомогательный метод для создания тестового shift_task."""
        from app.database.base import generate_uuid

        shift_task = ShiftTask(
            id=generate_uuid(),
            work_regime_id=1,
            vehicle_id=5,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
        )
        db_session.add(shift_task)
        await db_session.flush()
        return shift_task

    @pytest.mark.asyncio
    async def test_create_route_task_saves_to_db(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: создание route_task сохраняется в БД."""
        # Создаем тестовый shift_task
        test_shift_task = await self._create_test_shift_task(test_db_session)

        route_data = RouteTaskCreate(
            shift_task_id=test_shift_task.id,
            route_order=0,
            place_a_id=1,
            place_b_id=2,
            type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
            planned_trips_count=1,
            volume=1.0,
            weight=1.0,
        )

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    created_task = await RouteTaskService(test_db_session).create(
                        route_data=route_data,
                    )

        # Проверяем, что объект создан и имеет правильные данные
        assert created_task is not None
        assert created_task.id is not None
        assert created_task.shift_task_id == test_shift_task.id
        assert created_task.place_a_id == 1
        assert created_task.place_b_id == 2
        assert created_task.type_task == TypesRouteTaskEnum.LOADING_TRANSPORT_GM
        assert created_task.route_order == 0

    @pytest.mark.asyncio
    async def test_create_route_task_publishes_mqtt(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: создание route_task публикует событие в MQTT."""
        # Создаем тестовый shift_task
        test_shift_task = await self._create_test_shift_task(test_db_session)

        route_data = RouteTaskCreate(
            shift_task_id=test_shift_task.id,
            route_order=0,
            place_a_id=1,
            place_b_id=2,
            type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
            planned_trips_count=1,
            volume=1.0,
            weight=1.0,
        )

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await RouteTaskService(test_db_session).create(
                        route_data=route_data,
                    )

        # Проверяем, что MQTT клиент был вызван
        mock_mqtt_client.connect.assert_called_once()
        mock_mqtt_client.publish.assert_called()
        mock_mqtt_client.disconnect.assert_called_once()

        # Проверяем содержимое MQTT сообщения
        publish_calls = mock_mqtt_client.publish.call_args_list
        assert len(publish_calls) > 0

        # Проверяем первое сообщение (route_task)
        topic, payload = publish_calls[0][0]
        assert "truck/5/trip-service/events" in topic
        assert payload["event_type"] == "entity_changed"
        assert payload["entity_type"] == "route_task"
        assert payload["action"] == "create"

    @pytest.mark.asyncio
    async def test_create_route_task_publishes_redis_with_full_shift_task(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: создание route_task публикует полный shift_task в Redis."""
        # Создаем тестовый shift_task
        test_shift_task = await self._create_test_shift_task(test_db_session)

        route_data = RouteTaskCreate(
            shift_task_id=test_shift_task.id,
            route_order=0,
            place_a_id=1,
            place_b_id=2,
            type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
            planned_trips_count=1,
            volume=1.0,
            weight=1.0,
        )

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await RouteTaskService(test_db_session).create(
                        route_data=route_data,
                    )

        # Проверяем, что Redis publish был вызван
        assert mock_redis_client.publish.call_count > 0

        # Проверяем, что был вызов для shift_tasks канала (полный shift_task)
        publish_calls = mock_redis_client.publish.call_args_list
        shift_task_calls = [call for call in publish_calls if len(call[0]) > 0 and "shift_tasks:changes" in call[0][0]]
        assert len(shift_task_calls) > 0

        # Проверяем структуру сообщения
        import json

        channel, message = shift_task_calls[0][0]
        event_data = json.loads(message)
        assert event_data["event_type"] == "shift_task_changed"
        assert "shift_task" in event_data
        assert "route_tasks" in event_data["shift_task"]


class TestRouteTaskBulkServiceIntegration:
    """Интеграционные тесты для RouteTaskBulkService."""

    async def _create_test_shift_task(self, db_session):
        """Вспомогательный метод для создания тестового shift_task."""
        from app.database.base import generate_uuid

        shift_task = ShiftTask(
            id=generate_uuid(),
            work_regime_id=1,
            vehicle_id=5,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
        )
        db_session.add(shift_task)
        await db_session.flush()
        return shift_task

    @pytest.mark.asyncio
    async def test_bulk_upsert_creates_route_tasks_in_db(
        self,
        test_db_session,
        mock_mqtt_client,
        mock_redis_client,
    ):
        """Тест: bulk_upsert создает route_tasks в БД."""
        # Создаем тестовый shift_task
        test_shift_task = await self._create_test_shift_task(test_db_session)

        items = [
            RouteTaskBulkUpsertItem(
                shift_task_id=test_shift_task.id,
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                planned_trips_count=1,
                volume=1.0,
                weight=1.0,
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    result = await RouteTaskBulkService.bulk_upsert(
                        items=items,
                        db=test_db_session,
                        validate_shift_tasks=True,
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
        # Создаем тестовый shift_task
        test_shift_task = await self._create_test_shift_task(test_db_session)

        items = [
            RouteTaskBulkUpsertItem(
                shift_task_id=test_shift_task.id,
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                planned_trips_count=1,
                volume=1.0,
                weight=1.0,
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await RouteTaskBulkService.bulk_upsert(
                        items=items,
                        db=test_db_session,
                        validate_shift_tasks=True,
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
        # Создаем тестовый shift_task
        test_shift_task = await self._create_test_shift_task(test_db_session)

        items = [
            RouteTaskBulkUpsertItem(
                shift_task_id=test_shift_task.id,
                route_order=0,
                place_a_id=1,
                place_b_id=2,
                type_task=TypesRouteTaskEnum.LOADING_TRANSPORT_GM,
                planned_trips_count=1,
                volume=1.0,
                weight=1.0,
            ),
        ]

        with patch("app.services.tasks.task_event_publisher.TripServiceMQTTClient", return_value=mock_mqtt_client):
            with patch("app.services.tasks.task_event_publisher.redis_client.redis", mock_redis_client):
                with patch("app.core.config.settings.service_mode", "server"):
                    await RouteTaskBulkService.bulk_upsert(
                        items=items,
                        db=test_db_session,
                        validate_shift_tasks=True,
                        publish_mqtt=True,
                    )

        # Проверяем, что Redis publish был вызван
        assert mock_redis_client.publish.call_count > 0

        # Проверяем, что был вызов для shift_tasks канала (полный shift_task)
        publish_calls = mock_redis_client.publish.call_args_list
        shift_task_calls = [call for call in publish_calls if len(call[0]) > 0 and "shift_tasks:changes" in call[0][0]]
        assert len(shift_task_calls) > 0
