"""Билдинг FastStream приложения."""

from faststream import FastStream

from src.core.config import get_settings
from src.core.faststream.lifespan import lifespan
from src.core.faststream.rabbit_broker import broker

settings = get_settings()


def get_app() -> FastStream:
    """Получить FastStream приложение.

    Это главный конструктов приложения.

    Returns:
        FastStream приложение
    """
    app = FastStream(
        broker,
        lifespan=lifespan,
    )

    return app
