# ruff: noqa: S603
"""Главная функция для старта сервера."""

import uvicorn

from src.background import start_background_processes, stop_background_processes
from src.core.config import get_settings

settings = get_settings()


def main() -> None:
    """Точка входа в сервис."""
    background_processes = start_background_processes()
    try:
        uvicorn.run(
            app="src.core.fastapi.application:get_app",
            host=settings.HOST,
            port=settings.PORT,
            reload=True if settings.MODE == "local" else False,
            log_level="info",
            factory=True,
            forwarded_allow_ips="*",
            log_config=None,
            access_log=False,
        )
    finally:
        stop_background_processes(background_processes)


if __name__ == "__main__":
    main()
