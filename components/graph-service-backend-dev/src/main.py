"""FastAPI приложение для graph-service."""

import asyncio
import os
from contextlib import asynccontextmanager

from audit_lib.fastapi import AuditMiddleware
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.middleware.logging import log_requests_middleware, setup_logger
from app.middleware.mqtt_publish import mqtt_publish_middleware
from app.services.locations import loc_finder

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения."""
    logger.info("Application startup", service="graph-service")

    # Запускаем миграции Alembic при старте
    try:
        from init_db import run_migrations

        await asyncio.to_thread(run_migrations)
        await loc_finder.add_db_tags()
        logger.info("Database migrations completed successfully", service="graph-service")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}", service="graph-service")
        logger.exception("Migration error details", service="graph-service")
        raise

    # Устанавливаем event loop для WebSocket broadcast из MQTT потока
    from app.core.websocket_client import set_event_loop

    loop = asyncio.get_running_loop()
    set_event_loop(loop)
    logger.info("Event loop set for WebSocket broadcasting")

    # Инициализация MQTT
    from app.core.mqtt.mqtt_client import init_mqtt_client, start_connection_checker

    init_mqtt_client()
    start_connection_checker()

    logger.info("Graph Service started successfully")

    yield

    await loc_finder.remove_db_tags()
    logger.info("Application shutdown")


app = FastAPI(
    title="Graph Service",
    description="Сервис для управления графами шахт",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


def _serializable_validation_errors(errors: list) -> list:
    """Преобразует ошибки валидации в JSON-сериализуемый вид (ctx может содержать Exception)."""
    result = []
    for err in errors:
        err_copy = err.copy()
        if "ctx" in err_copy and isinstance(err_copy["ctx"], dict):
            ctx = err_copy["ctx"].copy()
            for k, v in ctx.items():
                if isinstance(v, BaseException):
                    ctx[k] = str(v)
            err_copy["ctx"] = ctx
        result.append(err_copy)
    return result


# Обработчик ошибок валидации запросов
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Логирование ошибок валидации Pydantic."""
    logger.error(
        f"Validation error: path={request.url.path} method={request.method} errors={exc.errors()}",
    )
    return JSONResponse(
        status_code=400,
        content={"detail": _serializable_validation_errors(exc.errors())},
    )


# Обработчик всех необработанных исключений
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Логирование всех необработанных исключений."""
    import traceback

    logger.error(f"Unhandled exception: path={request.url.path} method={request.method}")
    logger.error(f"Exception: {type(exc).__name__}: {exc}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

# HTTP middlewares
app.middleware("http")(log_requests_middleware)
app.middleware("http")(mqtt_publish_middleware)


# --- Роутеры ---
from app.routers import api_router
from app.routers.ws_vehicle_tracking import websocket_router

app.include_router(api_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "service": "graph-service",
        "status": "running",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.core.mqtt.mqtt_client import get_mqtt_client

    mqtt_client = get_mqtt_client()
    mqtt_status = "connected" if mqtt_client and mqtt_client.is_connected() else "disconnected"

    return {
        "status": "healthy",
        "service": "graph-service",
        "mqtt": mqtt_status,
        "vehicle_id": os.getenv("VEHICLE_ID", "4"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # noqa: S104
        port=5000,
        reload=True,
    )
