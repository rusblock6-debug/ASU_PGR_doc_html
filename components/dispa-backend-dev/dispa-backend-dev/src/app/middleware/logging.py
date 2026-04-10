"""Middleware для логирования всех HTTP-запросов и ответов."""

import json
import os
import sys
import time
from datetime import date, datetime
from typing import Any

from fastapi import Request, Response
from loguru import logger

from app.core.logging_config import setup_logging


def _json_default(obj: object) -> str:
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


def setup_logger(
    *,
    log_level: str | None = None,
    console_output: bool = False,
    colorize: bool = True,
    console_format: str | None = None,
) -> None:
    """Настройка логера.

    По умолчанию остаётся JSON формат.
    Для локальной разработки можно включить цветной консольный вывод.
    """
    setup_logging(
        log_level=log_level or os.getenv("LOG_LEVEL", "INFO"),
        console_output=console_output,
        colorize=colorize,
        console_format=console_format,
    )


# Пути, которые не нужно логировать на уровне info (только ошибки)
SKIP_INFO_LOGGING = [
    "/health",
    "/healthcheck",
    "/metrics",
    "/favicon.ico",
    "/ws/",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/location/",  # Поиск меток (polling запросы)
]


def _should_log_request(path: str) -> bool:
    """Проверить, нужно ли логировать запрос на уровне info."""
    return not any(path.startswith(skip_path) for skip_path in SKIP_INFO_LOGGING)


async def log_requests_middleware(request: Request, call_next: Any) -> Response:
    """Middleware для логирования всех HTTP-запросов и ответов, включая ошибки.

    Служебные запросы (health, metrics, docs) логируются только при ошибках.
    """
    start_time = time.perf_counter()
    path = request.url.path
    should_log = _should_log_request(path)

    # Логируем входящий запрос только для важных путей
    if should_log:
        logger.info(
            "Incoming request",
            method=request.method,
            path=path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
            service="trip-service",
        )

    try:
        # Обрабатываем запрос
        response = await call_next(request)

        # Вычисляем время обработки
        process_time = time.perf_counter() - start_time

        # Логируем ответ в зависимости от статуса
        if response.status_code >= 500:
            # Всегда логируем ошибки сервера
            logger.error(
                "Request failed with server error",
                method=request.method,
                path=path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                service="trip-service",
            )
        elif response.status_code >= 400:
            # Всегда логируем ошибки клиента
            logger.warning(
                "Request failed with client error",
                method=request.method,
                path=path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                service="trip-service",
            )
        elif should_log:
            # Успешные запросы логируем только для важных путей
            logger.info(
                "Request completed successfully",
                method=request.method,
                path=path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                service="trip-service",
            )

        return response

    except Exception as e:
        # Вычисляем время обработки до момента ошибки
        process_time = time.perf_counter() - start_time

        # Всегда логируем исключения
        logger.error(
            "Request failed with exception",
            method=request.method,
            path=path,
            error_type=type(e).__name__,
            error_message=str(e),
            process_time_ms=round(process_time * 1000, 2),
            service="trip-service",
        )

        # Пробрасываем исключение дальше для обработки FastAPI
        raise
