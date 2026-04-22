"""Функции жизненного цикла для FastAPI приложения."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Never

from fastapi import FastAPI
from loguru import logger

from src.api.rest import main_router
from src.core.config import get_settings
from src.core.fastapi.initialization.router import init_main_router
from src.core.logger import configure_loguru

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[Never]:
    """Функция жизненного цикла FastAPI приложения(startup и shutdown новый)."""
    configure_loguru()
    init_main_router(app_=app, main_router=main_router)
    logger.info("Application startup complete")

    yield  # type: ignore[misc]

    logger.info("Application shutdown complete")
