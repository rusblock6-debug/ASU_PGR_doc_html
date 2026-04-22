"""Trip Service - FastAPI Application.

Основной модуль приложения с lifespan для инициализации и shutdown.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.exceptions.base import BaseResponseException
from app.api.routers import api_router, health_router
from app.api.schemas.error import APIError
from app.core.config import settings
from app.core.migrations import run_migrations
from app.core.redis_client import redis_client
from app.middleware.logging import log_requests_middleware, setup_logger
from app.services.event_handlers import disconnect_mqtt_client, initialize_mqtt_client
from app.services.tasks.scheduled import start_scheduled_tasks, stop_scheduled_tasks


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan context manager.

    Startup:
    - Настройка логирования
    - Подключение к Redis
    - Подключение к MQTT (Nanomq)
    - Подписка на топики Nanomq
    - Запуск периодических задач (только для server mode)
    - TODO: Cold start восстановление состояния

    Shutdown:
    - Остановка периодических задач
    - Отключение от Redis
    - Отключение от MQTT
    """
    # Startup
    setup_logger(
        log_level=settings.log_level,
        console_output=settings.debug,
    )
    logger.info(
        "Trip Service starting",
        version="1.0.0",
        vehicle_id=settings.vehicle_id,
        service_mode=settings.service_mode,
    )
    logger.info("Start lifespan")

    await run_migrations()

    try:
        # Подключение к Redis
        await redis_client.connect()

        # Инициализация и подключение к MQTT (Nanomq)
        await initialize_mqtt_client()

        # Запуск периодических задач (только для server mode)
        await start_scheduled_tasks()

        # TODO: Cold start восстановление состояния
        # await cold_start_recovery()

        logger.info("Trip Service started successfully")

        yield
    except Exception as exc:
        logger.error("Exception in lifespan", exc_info=exc)
    finally:
        logger.info("Stop lifespan")
        await stop_scheduled_tasks()

        await disconnect_mqtt_client()
        await redis_client.disconnect()
        logger.info("Trip Service stopped")


def create_app() -> FastAPI:
    """Создаёт и возвращает экземпляр FastAPI с lifespan и роутерами."""
    lifespan = app_lifespan
    # FastAPI application
    _app = FastAPI(
        title="Trip Service",
        version="1.0.0",
        description="Управление рейсами горной техники с State Machine",
        lifespan=lifespan,
        debug=settings.debug,
    )

    @_app.exception_handler(BaseResponseException)
    def handle_base_response_exception(_: Request, exc: BaseResponseException) -> JSONResponse:
        _error = APIError(code=exc.code, detail=exc.message)
        if hasattr(exc, "entity_id"):
            _error.entity_id = exc.entity_id

        return JSONResponse(
            content=_error.model_dump(mode="json", exclude_none=True),
            status_code=exc.status_code,
        )

    # Logging middleware для логирования всех HTTP запросов
    _app.middleware("http")(log_requests_middleware)

    # CORS middleware для работы с frontend
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Frontend в Docker
            "http://localhost:5173",  # Frontend dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://10.100.109.13:3000",  # Dev server на удаленном хосте
            "http://10.100.109.11:3000",
            "http://10.100.109.12:3000",
            "http://10.100.109.15:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    _app.include_router(api_router)
    _app.include_router(health_router)

    return _app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
