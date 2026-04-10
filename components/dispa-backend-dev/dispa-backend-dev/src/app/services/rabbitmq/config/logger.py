"""Настройка логирования в JSON формате для RabbitMQ сервисов."""

import json
import sys
from datetime import date, datetime
from typing import Any

from loguru import logger

from app.core.config import settings


def _json_default(obj: Any) -> str:
    """Функция для сериализации несериализуемых объектов в JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


# Конфигурация логирования в JSON формате
def json_sink(message: Any) -> None:
    """JSON sink для loguru."""
    record = message.record
    # Базовые поля
    log_entry = {
        "service": "trip-service",
        "level": record["level"].name,
        "message": record["message"],
        "time": record["time"].isoformat(),
    }

    # Добавляем информацию о файле и строке для отладки
    log_entry["pathname"] = record["file"].path
    log_entry["lineno"] = record["line"]

    # Добавляем extra поля из логирования
    for key, value in record["extra"].items():
        log_entry[key] = value

    # Выводим JSON в stdout без print() для избежания лишнего вывода
    sys.stdout.write(json.dumps(log_entry, ensure_ascii=False, default=_json_default) + "\n")
    sys.stdout.flush()


def get_logger() -> Any:
    """Настройка логера с JSON форматированием."""
    # Удаляем стандартный handler и добавляем JSON sink
    logger.remove()
    if settings.log_level == "DEBUG":
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | {message} | <dim>{extra}</dim>",
            level=settings.log_level,
            colorize=True,
        )
    else:
        logger.add(json_sink, level=settings.log_level)
    return logger
