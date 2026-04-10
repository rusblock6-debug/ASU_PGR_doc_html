"""Функции инициализации для FastAPI application."""

from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from src.core.fastapi.middleware import LoguruMiddleware, SQLAlchemyMiddleware


def init_middlewares() -> list[Middleware]:
    """Инициализация мидлваров."""
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "OPTIONS", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["*"],
        ),
        Middleware(SQLAlchemyMiddleware),
        Middleware(LoguruMiddleware),
    ]
    return middleware
