"""Middleware для автоматической публикации событий изменения сущностей в MQTT.
Работает только в серверном режиме (SERVICE_MODE=server).

Логика: всё что НЕ в чёрном списке SKIP_ENDPOINTS - публикуется.
"""

import json

from fastapi import Request
from loguru import logger

from app.services.event_publisher import event_publisher
from config.settings import get_settings

settings = get_settings()

# Эндпоинты, для которых НЕ нужно отправлять события (чёрный список)
SKIP_ENDPOINTS = [
    "/health",
    "/ws/",
    "/api/location/",  # Поиск меток
    "/api/ladder-nodes/",  # Лестницы публикуют события вручную в сервисе
    "/api/docs",  # Документация
    "/api/redoc",  # Документация
    "/api/openapi",  # OpenAPI схема
]


async def async_iterator_wrapper(items: list[bytes]):
    """Обертка для создания async iterator из списка."""
    for item in items:
        yield item


async def mqtt_publish_middleware(request: Request, call_next):
    """Middleware: автоматически публикует изменения в MQTT
    для всех POST/PUT/PATCH/DELETE запросов.
    """
    # Пропускаем если не серверный режим
    if not settings.is_server_mode:
        return await call_next(request)

    method = request.method.upper()
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        return await call_next(request)

    # Пропускаем эндпоинты из чёрного списка
    path = request.url.path
    for skip_path in SKIP_ENDPOINTS:
        if path.startswith(skip_path):
            return await call_next(request)

    # Выполняем запрос
    response = await call_next(request)

    # Публикуем событие только для успешных запросов
    if response.status_code < 200 or response.status_code >= 300:
        return response

    try:
        # Определяем тип сущности по URL
        path_parts = [p for p in path.split("/") if p]

        # Специальная обработка для импорта
        if "/import/" in path:
            entity_type = "import"
        else:
            # Пропускаем 'api' и берем следующую часть
            entity_type = None
            if len(path_parts) > 1:
                idx = 1 if path_parts[0] == "api" else 0
                if len(path_parts) > idx:
                    entity_path = path_parts[idx]
                    # Преобразуем множественное число в единственное
                    # horizons -> horizon, nodes -> node, places -> place
                    entity_type = entity_path.replace("-", "_")
                    if entity_type.endswith("s"):
                        entity_type = entity_type[:-1]

        if not entity_type:
            return response

        # Определяем действие
        action_map = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}
        action = action_map.get(method, "update")

        # Определяем ID сущности
        entity_id = None
        if method in ("PUT", "PATCH", "DELETE") and len(path_parts) > 2:
            potential_id = path_parts[-1]
            # Проверяем что это похоже на ID (число или UUID)
            if potential_id.isdigit() or len(potential_id) > 10:
                entity_id = potential_id

        # Для POST пытаемся взять ID из ответа
        elif method == "POST":
            try:
                resp_body = [section async for section in response.__dict__["body_iterator"]]
                response.__setattr__("body_iterator", async_iterator_wrapper(resp_body))
                try:
                    resp_body = json.loads(resp_body[0].decode())
                except Exception:
                    resp_body = str(resp_body)  # type: ignore[assignment]

                # Для import возвращаем horizon_id (один горизонт за импорт)
                if "/import/" in path:
                    horizon_ids = resp_body.get("horizon_ids", [])  # type: ignore[union-attr,attr-defined]
                    if horizon_ids:
                        entity_id = str(horizon_ids[0])
                else:
                    entity_id = resp_body.get("id")  # type: ignore[union-attr,attr-defined]
            except Exception:  # noqa: S110
                pass

        # Фильтруем сообщения: не отправляем если entity_type или entity_id невалидны
        if not entity_type or entity_type == "unknown" or not entity_id or entity_id == "unknown":
            logger.debug(
                "Skipping MQTT publish: invalid entity data",
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                path=path,
            )
            return response

        # Публикуем событие
        await event_publisher.publish_entity_changed(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
        )
        logger.info(
            f"Published entity change: entity_type={entity_type} "
            f"entity_id={entity_id} action={action}",
        )

    except Exception as e:
        logger.exception(f"mqtt_publish_middleware error: {e}")

    return response
