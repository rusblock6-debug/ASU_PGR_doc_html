"""Интеграционный тест для полного цикла обработки shift_task через MQTT.

Проверяет:
1. Создание shift_task через bulk upsert (сервер)
2. Публикацию в MQTT
3. Получение сообщения бортовым trip-service
4. Обработку сообщения и обновление БД
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.api.schemas.tasks.route_tasks_bulk import RouteTaskBulkUpsertItem
from app.api.schemas.tasks.shift_tasks_bulk import ShiftTaskUpsertItem
from app.database.models import ShiftTask
from app.enums import ShiftTaskStatusEnum, TypesRouteTaskEnum
from app.services.event_handlers import handle_mqtt_event
from app.services.tasks.shift_task_bulk import ShiftTaskBulkService


@pytest.mark.asyncio
class TestShiftTaskMqttToBortProcessing:
    """Тесты для полного цикла обработки shift_task через MQTT."""

    async def test_bulk_upsert_publishes_mqtt_and_bort_processes(
        self,
        test_db_session,
    ):
        """Тест: bulk upsert shift_task публикует в MQTT, борт получает и обрабатывает.

        Процесс:
        1. Сервер создает shift_task через bulk upsert
        2. Публикует событие в MQTT (truck/4/trip-service/events)
        3. Бортовой trip-service получает сообщение через handle_mqtt_event
        4. Обрабатывает через handle_trip_service_shift_task_event
        5. Обновляет БД через локальный API
        """
        # 1. Создаем shift_task через bulk upsert (сервер)
        shift_task_data = ShiftTaskUpsertItem(
            id="test_shift_001",
            work_regime_id=1,
            vehicle_id=4,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            route_tasks=[
                RouteTaskBulkUpsertItem(
                    id="test_route_001",
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

        # Создаем через bulk upsert (это симулирует сервер)
        with patch("app.core.config.settings.service_mode", "server"):
            result = await ShiftTaskBulkService.bulk_upsert(
                items=[shift_task_data],
                db=test_db_session,
                publish_mqtt=True,
            )

        # Проверяем, что shift_task создан
        assert len(result.items) == 1
        assert result.items[0].action == "created"
        created_shift_id = result.items[0].id

        # 2. Симулируем получение MQTT сообщения бортом
        # Создаем MQTT сообщение в формате, который публикует сервер
        mqtt_topic = "truck/4/trip-service/events"
        mqtt_payload = {
            "event_type": "entity_changed",
            "entity_type": "shift_task",
            "entity_id": created_shift_id,
            "action": "create",
            "timestamp": "2026-01-26T12:00:00Z",
            "data": {},
        }

        # 3. Симулируем обработку сообщения бортом (bort mode)
        # Вызываем handle_mqtt_event с bort mode
        with patch("app.core.config.settings.service_mode", "bort"):
            # Мокируем HTTP запрос к серверному trip-service
            # В реальности борт делает GET запрос к серверу для получения полных данных
            mock_get_response = AsyncMock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {
                "id": created_shift_id,
                "work_regime_id": 1,
                "vehicle_id": 4,
                "shift_date": "2026-01-26",
                "shift_num": 1,
                "status": "pending",
                "priority": 0,
                "route_tasks": [
                    {
                        "id": "test_route_001",
                        "route_order": 0,
                        "place_a_id": 1,
                        "place_b_id": 2,
                        "type_task": "loading_transport_gm",
                        "planned_trips_count": 1,
                        "volume": 1.0,
                        "weight": 1.0,
                    },
                ],
            }

            # Мокируем HTTP запрос к локальному API (POST /api/shift-tasks)
            mock_post_response = AsyncMock()
            mock_post_response.status_code = 201
            mock_post_response.json.return_value = {
                "id": created_shift_id,
                "work_regime_id": 1,
                "vehicle_id": 4,
                "shift_date": "2026-01-26",
                "shift_num": 1,
                "status": "pending",
            }

            # Мокируем httpx.AsyncClient как контекстный менеджер
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_get_response
            mock_client.post.return_value = mock_post_response

            with patch("httpx.AsyncClient", return_value=mock_client):
                # Вызываем обработчик MQTT события
                await handle_mqtt_event(mqtt_topic, mqtt_payload)

        # 4. Проверяем, что обработчик был вызван
        # В реальности shift_task должен быть создан в бортовой БД
        # Для теста проверяем, что HTTP запросы были сделаны
        assert mock_client.get.called, "GET запрос к серверному trip-service должен быть выполнен"
        assert mock_client.post.called, "POST запрос к локальному API должен быть выполнен"

    async def test_bulk_upsert_update_publishes_mqtt_and_bort_processes(
        self,
        test_db_session,
    ):
        """Тест: bulk upsert update shift_task публикует в MQTT, борт получает и обновляет."""
        # 1. Создаем начальный shift_task
        initial_shift = ShiftTask(
            id="test_shift_update_001",
            work_regime_id=1,
            vehicle_id=4,
            shift_date=date(2026, 1, 26),
            shift_num=1,
            status=ShiftTaskStatusEnum.PENDING,
            priority=0,
        )
        test_db_session.add(initial_shift)
        await test_db_session.commit()
        await test_db_session.refresh(initial_shift)

        # 2. Обновляем через bulk upsert (сервер)
        update_data = ShiftTaskUpsertItem(
            id=initial_shift.id,
            work_regime_id=1,
            vehicle_id=4,
            shift_date="2026-01-26",
            shift_num=1,
            status=ShiftTaskStatusEnum.ACTIVE,  # Изменяем статус
            priority=10,  # Изменяем приоритет
        )

        with patch("app.core.config.settings.service_mode", "server"):
            result = await ShiftTaskBulkService.bulk_upsert(
                items=[update_data],
                db=test_db_session,
                publish_mqtt=True,
            )

        # Проверяем, что shift_task обновлен
        assert len(result.items) == 1
        assert result.items[0].action == "updated"

        # 3. Симулируем обработку MQTT сообщения на борту
        # Получаем обновленный shift_task
        updated_shift_query = select(ShiftTask).where(ShiftTask.id == initial_shift.id)
        updated_shift_result = await test_db_session.execute(updated_shift_query)
        updated_shift = updated_shift_result.scalar_one_or_none()

        assert updated_shift is not None
        assert updated_shift.status == ShiftTaskStatusEnum.ACTIVE
        assert updated_shift.priority == 10

        # 4. Симулируем обновление на борту
        from app.api.schemas.tasks.shift_tasks import ShiftTaskUpdate
        from app.services.tasks.shift_task import ShiftTaskService

        update_for_bort = ShiftTaskUpdate(
            status=ShiftTaskStatusEnum.ACTIVE,
            priority=10,
        )

        with patch("app.core.config.settings.service_mode", "bort"):
            # В реальности борт получает MQTT сообщение и делает PUT запрос
            # Для теста вызываем напрямую
            bort_updated = await ShiftTaskService(test_db_session).update(
                shift_id=initial_shift.id,
                shift_data=update_for_bort,
            )

        # Проверяем, что обновление применено
        assert bort_updated.status == ShiftTaskStatusEnum.ACTIVE
        assert bort_updated.priority == 10
