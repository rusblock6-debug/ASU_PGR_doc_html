"""Настройка структурированного логирования через Loguru.

Все логи на английском, формат JSON для парсинга.
"""

import json
import os
import sys
from datetime import date, datetime
from typing import Any

from loguru import logger

DEFAULT_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level> | "
    "<dim>{extra}</dim>"
)


def _json_default(obj: object) -> str:
    """Сериализует объекты, которые не поддерживаются json.dumps по умолчанию."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


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


def setup_logging(
    *,
    log_level: str | None = None,
    console_output: bool = False,
    colorize: bool = True,
    console_format: str | None = None,
) -> None:
    """Настройка Loguru для структурированного JSON логирования.

    По умолчанию используется JSON sink для парсинга логов.
    Если `console_output=True`, включается цветной консольный формат.
    """
    # Удаляем дефолтный handler
    logger.remove()

    level: str = log_level if log_level is not None else (os.getenv("LOG_LEVEL") or "INFO")
    if console_output:
        logger.add(
            sys.stderr,
            level=level,
            colorize=colorize,
            format=console_format or DEFAULT_CONSOLE_FORMAT,
            backtrace=False,
            diagnose=False,
        )
    else:
        logger.add(
            json_sink,
            level=level,
        )

    logger.info("Logging configured successfully")
