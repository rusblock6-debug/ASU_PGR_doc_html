"""Конфигурация логирования с использованием Loguru."""

import json

import loguru
from loguru import logger
from loguru._logger import Logger

from app.core.config import settings


def json_sink(message: "loguru.Message") -> None:
    """Кастомный sink для JSON логирования с полями service, level, message, time."""
    record = message.record

    # Создаем JSON лог запись
    log_entry: dict[str, str] = {
        "service": "enterprise-service",
        "level": record["level"].name,
        "message": record["message"],
        "time": record["time"].isoformat(),
    }

    # Добавляем дополнительные поля из extra (кроме service, если он там есть)
    for key, value in record["extra"].items():
        if key != "service":  # service уже добавлен выше
            log_entry[key] = value

    # Выводим JSON строку
    print(json.dumps(log_entry, ensure_ascii=False, default=str))


def setup_logging() -> None:
    """Настройка логирования в JSON формате."""
    # Удалить стандартный handler
    logger.remove()

    # Добавить кастомный JSON sink
    logger.add(
        json_sink,
        level=settings.LOG_LEVEL,
        colorize=False,
    )


def get_logger(bound_logger: Logger, name: str = "base logger") -> Logger:
    """Получить логгер с привязанным именем."""
    return bound_logger.bind(name=name)  # type: ignore[no-untyped-call]
