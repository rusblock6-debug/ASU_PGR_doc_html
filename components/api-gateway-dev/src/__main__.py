"""Entry point for the API gateway."""

import logging

from aiohttp import web

from src.app import create_app
from src.config import Settings
from src.logging_setup import configure_logging


def main() -> None:
    """Start the application with JSON logging configured."""
    settings = Settings()
    configure_logging(
        service_name=settings.service_name,
        environment=settings.environment,
        log_level=settings.log_level,
    )

    logger = logging.getLogger(__name__)
    logger.info(
        "gateway_startup",
        extra={
            "event": "startup",
            "host": settings.host,
            "port": settings.port,
        },
    )

    app = create_app(settings)
    web.run_app(app, host=settings.host, port=settings.port, print=None)


if __name__ == "__main__":
    main()
