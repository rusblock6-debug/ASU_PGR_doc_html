"""SSE (Server-Sent Events) для real-time обновлений состояний."""

import asyncio
import json
from collections.abc import AsyncGenerator

from auth_lib.dependencies import require_permission
from auth_lib.permissions import Action, Permission
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from app.core.redis_client import redis_client

router = APIRouter(prefix="/events", tags=["events"])


async def event_stream(vehicle_id: str, request: Request) -> AsyncGenerator[str]:
    """Генератор событий SSE для подписки на изменения состояний.

    Слушает Redis pub/sub канал trip-service:vehicle:{vehicle_id}:events
    и отправляет события клиенту в формате SSE.
    """
    logger.info("SSE client connected", vehicle_id=vehicle_id)

    if redis_client.redis is None:
        logger.error("Redis client not connected for SSE event_stream")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis not connected'})}\n\n"
        return

    # Создаем подписку на Redis pub/sub
    pubsub = redis_client.redis.pubsub()
    event_channel = f"trip-service:vehicle:{vehicle_id}:events"
    await pubsub.subscribe(event_channel)

    try:
        # Отправляем начальное событие подключения
        yield f"data: {json.dumps({'type': 'connected', 'vehicle_id': vehicle_id})}\n\n"

        # Слушаем события из Redis
        while True:
            # Проверяем, не отключился ли клиент
            if await request.is_disconnected():
                logger.info("SSE client disconnected", vehicle_id=vehicle_id)
                break

            # Ждем сообщение из Redis с таймаутом
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=1.0,
                )

                if message and message["type"] == "message":
                    # Отправляем событие клиенту
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    logger.debug("Sending SSE event", vehicle_id=vehicle_id, data=data)
                    yield f"data: {data}\n\n"

            except TimeoutError:
                # Отправляем heartbeat каждую секунду для поддержания соединения
                yield ": heartbeat\n\n"

    except Exception as e:
        logger.error("SSE stream error", vehicle_id=vehicle_id, error=str(e))
    finally:
        await pubsub.unsubscribe(event_channel)
        await pubsub.close()
        logger.info("SSE connection closed", vehicle_id=vehicle_id)


async def trips_event_stream(request: Request) -> AsyncGenerator[str]:
    """Генератор событий SSE для подписки на изменения рейсов (trips).

    Слушает Redis pub/sub канал trip-service:trips:changes
    и отправляет события клиенту в формате SSE.

    События:
    - created: новый рейс создан
    - updated: рейс обновлен
    - deleted: рейс удален
    """
    logger.info("SSE trips client connected")

    if redis_client.redis is None:
        logger.error("Redis client not connected for SSE trips_event_stream")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis not connected'})}\n\n"
        return

    pubsub = redis_client.redis.pubsub()
    channel = "trip-service:trips:changes"
    await pubsub.subscribe(channel)

    try:
        # Отправляем начальное событие подключения
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"

        # Слушаем события из Redis
        while True:
            # Проверяем, не отключился ли клиент
            if await request.is_disconnected():
                logger.info("SSE trips client disconnected")
                break

            # Ждем сообщение из Redis с таймаутом
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=1.0,
                )

                if message and message["type"] == "message":
                    # Отправляем событие клиенту
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    logger.debug("Sending SSE trips event", data=data)
                    yield f"data: {data}\n\n"

            except TimeoutError:
                # Отправляем heartbeat каждую секунду для поддержания соединения
                yield ": heartbeat\n\n"

    except Exception as e:
        logger.error("SSE trips stream error", error=str(e))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info("SSE trips connection closed")


async def all_events_stream(request: Request) -> AsyncGenerator[str]:
    """Генератор событий SSE для подписки на все события от всех транспортных средств.

    Слушает Redis pub/sub паттерн trip-service:vehicle:*:events
    и отправляет события клиенту в формате SSE.

    События:
    - state_transition - изменение состояния машины
    - trip_started - начало рейса
    - trip_completed - завершение рейса
    - cycle_started - начало цикла
    - cycle_completed - завершение цикла
    """
    logger.info("SSE all events client connected")

    if redis_client.redis is None:
        logger.error("Redis client not connected for SSE all_events_stream")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis not connected'})}\n\n"
        return

    pubsub = redis_client.redis.pubsub()
    pattern = "trip-service:vehicle:*:events"
    await pubsub.psubscribe(pattern)

    try:
        yield f"data: {json.dumps({'type': 'connected', 'pattern': pattern})}\n\n"

        while True:
            if await request.is_disconnected():
                logger.info("SSE all events client disconnected")
                break

            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=1.0,
                )

                if message and message["type"] == "pmessage":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    logger.debug("Sending SSE all events", channel=message["channel"], data=data)
                    yield f"data: {data}\n\n"

            except TimeoutError:
                yield ":heartbeat\n\n"

    except Exception as e:
        logger.error("SSE all events stream error", error=str(e))
    finally:
        await pubsub.punsubscribe(pattern)
        await pubsub.close()
        logger.info("SSE all events connection closed")


@router.get("/stream/all", dependencies=[Depends(require_permission((Permission.WORK_TIME_MAP, Action.VIEW)))])
async def stream_all_events(request: Request) -> StreamingResponse:
    """SSE endpoint для получения real-time обновлений всех событий от всех транспортных средств.

    Клиент подключается к этому endpoint и получает события в формате SSE:
    - state_transition - изменение состояния машины
    - trip_started - начало рейса
    - trip_completed - завершение рейса
    - cycle_started - начало цикла
    - cycle_completed - завершение цикла

    Формат события:
    {
        "event_type": "state_transition" | "trip_started" | "trip_completed" | "cycle_started" | "cycle_completed",
        "vehicle_id": 4,
        "cycle_id": "uuid_vehicle_id",
        "state": "moving_loaded",
        "timestamp": 1699356000.123,
        "history_id": "uuid_vehicle_id"
    }

    Example:
        ```javascript
        const eventSource = new EventSource('/api/events/stream/all');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event_type === 'state_transition') {
                // Обработка изменения состояния
                console.log('Vehicle:', data.vehicle_id, 'State:', data.state);
            }
        };
        ```
    """
    return StreamingResponse(
        all_events_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/trips")
async def stream_trips_events(request: Request) -> StreamingResponse:
    """SSE endpoint для получения real-time обновлений рейсов.

    Клиент подключается к этому endpoint и получает события в формате SSE:
    - created - новый рейс создан
    - updated - рейс обновлен
    - deleted - рейс удален

    Формат события:
    {
        "event_type": "created" | "updated" | "deleted",
        "trip": { ... полные данные рейса ... },
        "timestamp": "2024-01-01T12:00:00"
    }

    Example:
        ```javascript
        const eventSource = new EventSource('/api/events/stream/trips');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event_type === 'created') {
                // Добавить новый рейс в список
            } else if (data.event_type === 'updated') {
                // Обновить существующий рейс
            } else if (data.event_type === 'deleted') {
                // Удалить рейс из списка
            }
        };
        ```
    """
    return StreamingResponse(
        trips_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/shift-tasks", dependencies=[Depends(require_permission((Permission.WORK_ORDER, Action.VIEW)))])
async def stream_shift_tasks(request: Request) -> StreamingResponse:
    """SSE endpoint для получения real-time обновлений shift_tasks с route_tasks.

    Клиент подключается к этому endpoint и получает события в формате SSE:
    - create: новый shift_task создан
    - update: shift_task обновлен (включая изменения route_tasks)
    - delete: shift_task удален

    Формат события:
    {
        "event_type": "shift_task_changed",
        "action": "create" | "update" | "delete",
        "shift_task_id": "ST001",
        "vehicle_id": 4,
        "shift_task": {
            "id": "ST001",
            "work_regime_id": 1,
            "vehicle_id": 4,
            "shift_date": "2024-01-19",
            "shift_num": 1,
            "status": "pending",
            "route_tasks": [...],
            ...
        },
        "timestamp": "2024-01-19T12:00:00Z"
    }

    Example:
        ```javascript
        const eventSource = new EventSource('/api/events/stream/shift-tasks');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event_type === 'shift_task_changed') {
                if (data.action === 'create') {
                    // Добавить shift_task в список
                    addShiftTask(data.shift_task);
                } else if (data.action === 'update') {
                    // Обновить существующий shift_task
                    updateShiftTask(data.shift_task);
                } else if (data.action === 'delete') {
                    // Удалить shift_task
                    removeShiftTask(data.shift_task_id);
                }
            }
        };
        ```
    """
    return StreamingResponse(
        shift_tasks_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/{vehicle_id}")
async def stream_events(vehicle_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint для получения real-time обновлений состояний vehicle.

    Клиент подключается к этому endpoint и получает события в формате SSE:
    - state_event - события канала состояния `trip-service:vehicle:{vehicle_id}:events`
    - assignments_alert - события канала назначений `trip-service:vehicle:{vehicle_id}:alert`
    - location_event - события канала меток `truck/{vehicle_id}/sensor/tag/events`
    - weight_event - события канала веса `truck/{vehicle_id}/sensor/weight/events`
    - wifi_event - события канала wifi `truck/{vehicle_id}/sensor/wifi/fake_events`

    Example:
        ```javascript
        const eventSource = new EventSource('/api/events/stream/4');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            // data.event_type: state_event | assignments_alert | location_event | weight_event
            console.log('Event:', data);
        };
        ```
    """
    return StreamingResponse(
        combined_event_stream(vehicle_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Отключаем буферизацию nginx
        },
    )


async def tag_event_stream(vehicle_id: str, request: Request) -> AsyncGenerator[str]:
    """Генератор событий SSE для подписки на изменения локации (tag events).

    Слушает Redis pub/sub канал truck/{vehicle_id}/sensor/tag/events
    и отправляет события клиенту в формате SSE.
    """
    logger.info("SSE tag client connected", vehicle_id=vehicle_id)

    if redis_client.redis is None:
        logger.error("Redis client not connected for SSE tag_event_stream")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis not connected'})}\n\n"
        return

    # Создаем подписку на Redis pub/sub для tag events
    pubsub = redis_client.redis.pubsub()
    channel = f"truck/{vehicle_id}/sensor/tag/events"
    await pubsub.subscribe(channel)

    try:
        # Отправляем начальное событие подключения
        yield f"data: {json.dumps({'type': 'connected', 'vehicle_id': vehicle_id})}\n\n"

        # Слушаем события из Redis
        while True:
            # Проверяем, не отключился ли клиент
            if await request.is_disconnected():
                logger.info("SSE tag client disconnected", vehicle_id=vehicle_id)
                break

            # Ждем сообщение из Redis с таймаутом
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=1.0,
                )

                if message and message["type"] == "message":
                    # Отправляем событие клиенту
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    logger.debug("Sending SSE tag event", vehicle_id=vehicle_id, data=data)
                    yield f"data: {data}\n\n"

            except TimeoutError:
                # Отправляем heartbeat каждую секунду для поддержания соединения
                yield ": heartbeat\n\n"

    except Exception as e:
        logger.error("SSE tag stream error", vehicle_id=vehicle_id, error=str(e))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info("SSE tag connection closed", vehicle_id=vehicle_id)


async def weight_event_stream(vehicle_id: str, request: Request) -> AsyncGenerator[str]:
    """Генератор событий SSE для передачи информации о текущем весе."""
    logger.info("SSE weight client connected", vehicle_id=vehicle_id)

    if redis_client.redis is None:
        logger.error("Redis client not connected for SSE weight_event_stream")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis not connected'})}\n\n"
        return

    pubsub = redis_client.redis.pubsub()
    channel = f"truck/{vehicle_id}/sensor/weight/events"
    await pubsub.subscribe(channel)

    try:
        yield f"data: {json.dumps({'type': 'connected', 'vehicle_id': vehicle_id})}\n\n"

        latest_key = f"trip-service:vehicle:{vehicle_id}:current_weight"
        latest_weight = await redis_client.get_json(latest_key)
        if latest_weight:
            yield f"data: {json.dumps(latest_weight)}\n\n"

        while True:
            if await request.is_disconnected():
                logger.info("SSE weight client disconnected", vehicle_id=vehicle_id)
                break

            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=1.0,
                )

                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    logger.debug("Sending SSE weight event", vehicle_id=vehicle_id, data=data)
                    yield f"data: {data}\n\n"

            except TimeoutError:
                yield ": heartbeat\n\n"

    except Exception as e:
        logger.error("SSE weight stream error", vehicle_id=vehicle_id, error=str(e))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info("SSE weight connection closed", vehicle_id=vehicle_id)


async def shift_tasks_event_stream(request: Request) -> AsyncGenerator[str]:
    """Генератор событий SSE для подписки на изменения shift_tasks.

    Слушает Redis pub/sub канал trip-service:shift_tasks:changes
    и отправляет события клиенту в формате SSE.

    События:
    - create: новый shift_task создан
    - update: shift_task обновлен (включая изменения route_tasks)
    - delete: shift_task удален
    """
    logger.info("SSE shift_tasks client connected")

    # Проверяем, что Redis подключен
    if redis_client.redis is None:
        logger.error("Redis client not connected for SSE shift_tasks")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis client not connected'})}\n\n"
        return

    pubsub = redis_client.redis.pubsub()
    channel = "trip-service:shift_tasks:changes"
    await pubsub.subscribe(channel)
    logger.info(f"Subscribed to Redis channel: {channel}")

    # Ждем подтверждения подписки, чтобы убедиться, что мы действительно подписаны
    # Это важно для гарантии, что мы не пропустим сообщения
    try:
        subscribe_msg = await asyncio.wait_for(pubsub.get_message(timeout=2.0), timeout=2.0)
        if subscribe_msg and subscribe_msg.get("type") == "subscribe":
            logger.info(
                f"Successfully subscribed to Redis channel: {channel}, "
                f"subscribers: {subscribe_msg.get('data', 'unknown')}",
            )
        else:
            logger.warning(f"Unexpected subscribe message: {subscribe_msg}")
    except TimeoutError:
        logger.warning(f"Subscribe confirmation timeout for channel: {channel}")

    try:
        # Отправляем начальное событие подключения
        yield f"data: {json.dumps({'type': 'connected', 'channel': channel})}\n\n"

        # Слушаем события из Redis
        while True:
            # Проверяем, не отключился ли клиент
            if await request.is_disconnected():
                logger.info("SSE shift_tasks client disconnected")
                break

            # Ждем сообщение из Redis с таймаутом
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=1.0,
                )

                if message:
                    msg_type = message.get("type")
                    msg_channel = message.get("channel")

                    logger.debug(f"Received Redis message: type={msg_type}, channel={msg_channel}")

                    if msg_type == "message":
                        # Отправляем событие клиенту
                        data = message["data"]

                        # Redis клиент настроен с decode_responses=True, но проверяем на всякий случай
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        elif not isinstance(data, str):
                            data = str(data)

                        logger.info(
                            "Sending SSE shift_tasks event to client",
                            channel=msg_channel,
                            data_length=len(data),
                            data_preview=data[:100] if len(data) > 100 else data,
                        )
                        yield f"data: {data}\n\n"
                    elif msg_type == "subscribe":
                        logger.info(f"Subscribed to Redis channel: {msg_channel}")
                    else:
                        logger.debug(f"Ignoring Redis message type: {msg_type}, channel: {msg_channel}")

            except TimeoutError:
                # Отправляем heartbeat каждую секунду для поддержания соединения
                yield ": heartbeat\n\n"

    except Exception as e:
        logger.error("SSE shift_tasks stream error", error=str(e))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        logger.info("SSE shift_tasks connection closed")


async def combined_event_stream(vehicle_id: str, request: Request) -> AsyncGenerator[str]:
    """Объединенный генератор SSE для vehicle.

    Подписывается на 5 Redis-канала:
    - `trip-service:vehicle:{vehicle_id}:events` -> `event_type="state_event"`
    - `trip-service:vehicle:{vehicle_id}:alert` -> `event_type="assignments_alert"`
    - `truck/{vehicle_id}/sensor/tag/events` -> `event_type="location_event"`
    - `truck/{vehicle_id}/sensor/weight/events` -> `event_type="weight_event"`
    - `truck/{vehicle_id}/sensor/wifi/fake_events` -> `event_type="wifi_events"`

    Дополнительно при подключении отправляет последнее значение веса из
    `trip-service:vehicle:{vehicle_id}:current_weight` (если есть).
    """
    logger.info("SSE combined client connected", vehicle_id=vehicle_id)

    if redis_client.redis is None:
        logger.error("Redis client not connected for SSE combined_event_stream")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Redis not connected'})}\n\n"
        return

    # Создаем подписки на каналы Redis pub/sub, включая alert для диспетчерских назначений
    pubsub = redis_client.redis.pubsub()

    state_channel = f"trip-service:vehicle:{vehicle_id}:events"
    alert_channel = f"trip-service:vehicle:{vehicle_id}:alert"
    location_channel = f"truck/{vehicle_id}/sensor/tag/events"
    weight_channel = f"truck/{vehicle_id}/sensor/weight/events"
    wifi_channel = f"truck/{vehicle_id}/sensor/wifi/fake_events"

    await pubsub.subscribe(state_channel, alert_channel, location_channel, weight_channel, wifi_channel)

    # Кэш последних значений по типам событий
    last_values = {}

    try:
        # Отправляем начальное событие подключения
        yield f"data: {json.dumps({'type': 'connected', 'vehicle_id': vehicle_id})}\n\n"

        # Загружаем и отправляем последнее значение веса при подключении
        latest_weight_key = f"trip-service:vehicle:{vehicle_id}:current_weight"
        latest_weight = await redis_client.get_json(latest_weight_key)
        if latest_weight:
            latest_weight_with_type = {"event_type": "weight_event", **latest_weight}
            last_values["weight_event"] = latest_weight_with_type
            yield f"data: {json.dumps(latest_weight_with_type)}\n\n"

        # Слушаем события из Redis
        while True:
            # Проверяем, не отключился ли клиент
            if await request.is_disconnected():
                logger.info("SSE combined client disconnected", vehicle_id=vehicle_id)
                break

            # Ждем сообщение из Redis с таймаутом
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=1.0,
                )

                if message and message["type"] == "message":
                    # Получаем данные и канал
                    data = message["data"]
                    channel = message["channel"]

                    if isinstance(data, bytes):
                        data = data.decode("utf-8")

                    try:
                        # Пробуем распарсить JSON и добавить event_type
                        parsed_data = json.loads(data)
                    except json.JSONDecodeError:
                        # Если не JSON, оборачиваем в объект
                        parsed_data = {"raw_data": data}

                    # Определяем тип события по каналу
                    if channel == state_channel:
                        event_type = "state_event"
                    elif channel == alert_channel:
                        event_type = "assignments_alert"
                    elif channel == location_channel:
                        event_type = "location_event"
                    elif channel == weight_channel:
                        event_type = "weight_event"
                    elif channel == wifi_channel:
                        event_type = "wifi_event"
                    else:
                        event_type = "unknown_event"

                    # Добавляем event_type и vehicle_id в данные
                    parsed_data["event_type"] = event_type

                    # Проверяем, изменилось ли значение
                    if last_values.get(event_type) != parsed_data:
                        last_values[event_type] = parsed_data.copy()
                        logger.debug("Sending SSE combined event", event_type=event_type, data=parsed_data)
                        yield f"data: {json.dumps(parsed_data)}\n\n"
                    else:
                        logger.debug("Skipping duplicate SSE combined event", event_type=event_type, data=parsed_data)

            except TimeoutError:
                # Отправляем heartbeat каждую секунду для поддержания соединения
                yield ": heartbeat\n\n"

    except Exception as e:
        logger.error("SSE combined stream error", vehicle_id=vehicle_id, error=str(e))
    finally:
        await pubsub.unsubscribe(state_channel, alert_channel, location_channel, weight_channel, wifi_channel)
        await pubsub.close()
        logger.info("SSE combined connection closed", vehicle_id=vehicle_id)
