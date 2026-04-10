"""Билдинг FastAPI приложения."""

from fastapi import FastAPI
from fastapi.responses import UJSONResponse

from src.core.config import get_settings
from src.core.dto.type.app_mode import ModeType
from src.core.fastapi.initialization.listener import (
    init_ujson_for_custom_http_exception,
    init_ujson_for_exception,
)
from src.core.fastapi.initialization.middleware.init import init_middlewares
from src.core.fastapi.lifespan import lifespan

settings = get_settings()


def get_app() -> FastAPI:
    """Получить FastAPI приложение.

    Это главный конструктов приложения.

    Returns:
        FastAPI приложение
    """
    app = FastAPI(
        title=settings.PROJECT_INFO.get_project_name(),
        version=settings.PROJECT_INFO.get_project_version(),
        description=settings.PROJECT_INFO.get_project_description(),
        docs_url=None if settings.MODE == ModeType.production else "/api/v1/docs",
        openapi_url=(None if settings.MODE == ModeType.production else "/api/v1/openapi.json"),
        redoc_url=None if settings.MODE == ModeType.production else "/api/v1/redoc",
        default_response_class=UJSONResponse,
        middleware=init_middlewares(),
        lifespan=lifespan,
    )

    # Инициализация UJSON-обработчиков ошибок
    init_ujson_for_custom_http_exception(app_=app, loguru_logger=True)
    init_ujson_for_exception(app_=app, loguru_logger=True)

    return app
