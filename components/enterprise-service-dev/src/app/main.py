"""FastAPI приложение для enterprise-service."""

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from audit_lib.fastapi import AuditMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from loguru import logger

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.engine import get_db_session
from app.middleware import log_requests_middleware
from app.routers import (
    api,
    enterprise,
    health,
    load_type,
    load_type_category,
    organization_categories,
    shift_service,
    statuses,
    sync,
    vehicle_models,
    vehicles,
    work_regimes,
)
from app.services import SyncService

# Импорт EventPublisher
from app.services.event_publisher import EventPublisher

# Настройка логирования
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Жизненный цикл приложения."""
    logger.info("Application startup", service="enterprise-service")

    # Запускаем миграции Alembic при старте
    try:
        from init_db import run_migrations

        await asyncio.to_thread(run_migrations)
        logger.info(
            "Database migrations completed successfully",
            service="enterprise-service",
        )
    except Exception as e:
        logger.error(
            f"Failed to run database migrations: {e}",
            service="enterprise-service",
        )
        logger.exception("Migration error details", service="enterprise-service")
        raise

    # При запуске в режиме борта — сразу тянем данные с сервера
    async def _run_board_sync_on_startup() -> None:
        if settings.DEPLOYMENT_MODE.lower() != "board":
            return

        if not settings.SYNC_ON_START:
            logger.info("Board startup sync is disabled via settings", service="enterprise-service")
            return

        if not settings.SERVER_SYNC_BASE_URL:
            logger.warning(
                "Board startup sync skipped: SERVER_SYNC_BASE_URL is not configured",
                service="enterprise-service",
            )
            return

        try:
            async for db in get_db_session():
                summary = await SyncService.sync_from_server(
                    db=db,
                    base_url=settings.SERVER_SYNC_BASE_URL,
                    export_path=settings.SYNC_EXPORT_PATH,
                    timeout=settings.SYNC_HTTP_TIMEOUT,
                )
                logger.info(
                    "Board startup sync completed",
                    service="enterprise-service",
                    summary=summary,
                )
                break
        except Exception as exc:
            logger.exception(
                "Board startup sync failed",
                service="enterprise-service",
                error=str(exc),
            )

    # Не блокируем запуск приложения
    asyncio.create_task(_run_board_sync_on_startup())

    yield

    logger.info("Application shutdown")


app = FastAPI(
    title="Enterprise Service",
    description="Core сервис для управления статичными данными предприятия",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для логирования запросов
app.middleware("http")(log_requests_middleware)
app.add_middleware(AuditMiddleware)


class async_iterator_wrapper:
    """Обёртка для преобразования итератора в асинхронный итератор."""

    def __init__(self, obj: Any) -> None:
        """Инициализация обёртки."""
        self._it = iter(obj)

    def __aiter__(self) -> "async_iterator_wrapper":
        """Возвращает асинхронный итератор."""
        return self

    async def __anext__(self) -> Any:
        """Возвращает следующий элемент."""
        try:
            value = next(self._it)
        except StopIteration:
            raise StopAsyncIteration from None
        return value


@app.middleware("http")
async def mqtt_publish_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Middleware: автоматически публикует изменения в MQTT/Redis.

    Для всех POST/PUT/DELETE запросов, используя тело запроса.
    """
    method = request.method.upper()
    if method not in ("POST", "PUT", "DELETE"):
        return await call_next(request)

    action_map = {"POST": "create", "PUT": "update", "DELETE": "delete"}
    action = action_map[method]

    response = await call_next(request)

    # Проверяем флаг пропуска MQTT публикации
    if hasattr(request.state, "skip_mqtt_publish") and request.state.skip_mqtt_publish:
        logger.info(
            "Skipping MQTT publish due to skip_mqtt_publish flag",
            path=request.url.path,
            method=method,
        )
        return response

    try:
        # Определяем тип сущности по URL (пример: /api/vehicles → vehicle)
        path_parts = [p for p in request.url.path.split("/") if p]

        # Пропускаем 'api' и берем следующую часть
        entity_type = None
        if len(path_parts) > 1:
            # Получаем часть после /api/
            idx = 1 if path_parts[0] == "api" else 0
            if len(path_parts) > idx:
                entity_type = path_parts[idx]
                entity_type = entity_type.replace("-", "_")
                # Убираем 's' в конце только для стандартных множественных форм
                if entity_type.endswith("s") and entity_type not in [
                    "statuses",
                    "regimes",
                ]:
                    entity_type = entity_type[:-1]
                # Специальная обработка для некоторых типов
                if entity_type == "statuse":
                    entity_type = "status"
                elif entity_type == "work_regime":
                    entity_type = "work_regime"

        # Определяем id: для PUT/DELETE берем из URL, для POST — из ответа (если есть)
        entity_id = None
        if method in ("PUT", "DELETE") and len(path_parts) > 2:
            entity_id = path_parts[-1]

        # Для POST можно попытаться взять id из JSON ответа
        elif method == "POST":
            try:
                resp_body_parts = [section async for section in response.__dict__["body_iterator"]]
                response.__setattr__("body_iterator", async_iterator_wrapper(resp_body_parts))
                try:
                    parsed_body = json.loads(resp_body_parts[0].decode())
                except Exception:
                    parsed_body = None
                if isinstance(parsed_body, dict):
                    entity_id = parsed_body.get("id")
            except Exception:
                logger.debug("Failed to parse POST response body")

        # Фильтруем сообщения: не отправляем если entity_type или entity_id невалидны
        if not entity_type or entity_type == "unknown" or not entity_id or entity_id == "unknown":
            logger.warning(
                "Skipping MQTT publish: invalid entity data",
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                path=request.url.path,
            )
            return response

        # Получаем сессию БД для MQTT публикации
        async for db in get_db_session():
            # Публикуем событие
            await EventPublisher().publish_entity_changed(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                send_to_mqtt=True,
                send_to_redis=True,
                db=db,
            )
            logger.info(
                f"Published entity change: entity_type={entity_type}"
                f" entity_id={entity_id} action={action}",
            )
            break  # Закрываем генератор после использования

    except Exception as e:
        logger.exception(f"mqtt_publish_middleware error: {e}")

    return response


# --- Роутеры ---
app.include_router(health.router)
app.include_router(api.router)
app.include_router(enterprise.router, prefix="/api")
app.include_router(work_regimes.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(vehicle_models.router, prefix="/api")
app.include_router(statuses.router, prefix="/api")
app.include_router(organization_categories.router, prefix="/api")
app.include_router(load_type.router, prefix="/api")
app.include_router(load_type_category.router, prefix="/api")
app.include_router(shift_service.router, prefix="/api")
app.include_router(sync.router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Корневой endpoint."""
    return {
        "service": "enterprise-service",
        "status": "running",
        "version": "1.0.0",
        "documentation": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
    )
