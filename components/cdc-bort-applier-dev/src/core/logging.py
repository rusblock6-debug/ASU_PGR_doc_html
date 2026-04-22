import logging
import sys
from enum import Enum

import msgspec
from loguru import logger


class LogFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


class LogConfig(msgspec.Struct, frozen=True):
    """Конфигурация логирования."""

    level: int = logging.INFO
    format: LogFormat = LogFormat.TEXT
    colorize: bool = True
    backtrace: bool = True
    diagnose: bool = False  # Отключить в production для безопасности


TEXT_FORMAT = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)


def setup_logging(config: LogConfig | None = None) -> None:
    """Настраивает логирование с заданной конфигурацией."""
    if config is None:
        config = LogConfig()

    logger.remove()

    if config.format == LogFormat.JSON:
        logger.add(
            sys.stderr,
            level=config.level,
            serialize=True,
            backtrace=config.backtrace,
            diagnose=config.diagnose,
        )
    else:
        logger.add(
            sys.stderr,
            level=config.level,
            format=TEXT_FORMAT,
            colorize=config.colorize,
            backtrace=config.backtrace,
            diagnose=config.diagnose,
        )
