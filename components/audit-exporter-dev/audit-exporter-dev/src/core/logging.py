"""Loguru logging configuration with stdlib interception."""

import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Route stdlib logging records to loguru.

    Installed on the root logger so that uvicorn, FastAPI, and any other
    library that uses ``logging.getLogger()`` emits through loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Map stdlib level to loguru level name.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the originating frame so loguru reports correct caller info.
        frame_obj, depth = logging.currentframe(), 2
        while frame_obj and frame_obj.f_code.co_filename == logging.__file__:
            frame_obj = frame_obj.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: str = "INFO") -> None:
    """Configure loguru as the single logging backend.

    * Removes default loguru sink and adds a JSON sink to stdout.
    * Installs ``InterceptHandler`` on the stdlib root logger so that
      uvicorn / FastAPI / third-party logs are routed through loguru.
    * Log level is controlled by the ``log_level`` parameter.
    """
    # Remove default loguru handler.
    logger.remove()

    # Add structured sink to stdout.
    logger.add(
        sys.stdout,
        level=log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )

    # Intercept stdlib logging.
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Explicitly override uvicorn loggers that configure their own handlers.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = [InterceptHandler()]
        uv_logger.propagate = False
