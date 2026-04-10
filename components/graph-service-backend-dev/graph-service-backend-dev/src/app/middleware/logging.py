"""Middleware для логирования всех HTTP-запросов и ответов."""

import json
import os
import sys
import time

from fastapi import Request
from loguru import logger


# Конфигурация логирования в JSON формате
def json_sink(message):
    """JSON sink для loguru."""
    record = message.record
    # Базовые поля
    log_entry = {
        "service": "graph-service",
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
    sys.stdout.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def setup_logger():
    """Настройка логера с JSON форматированием."""
    # Удаляем стандартный handler и добавляем JSON sink
    logger.remove()
    logger.add(
        json_sink,
        level=os.getenv("LOG_LEVEL", "INFO"),
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


async def log_requests_middleware(request: Request, call_next):
    """Middleware для логирования всех HTTP-запросов и ответов, включая ошибки.
    Служебные запросы (health, metrics, docs) логируются только при ошибках.
    """
    start_time = time.perf_counter()
    path = request.url.path
    should_log = _should_log_request(path)

    # Логируем входящий запрос только для важных путей
    if should_log:
        logger.info(
            f"Incoming request: {request.method} {path}",
            method=request.method,
            path=path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
            service="graph-service",
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
                service="graph-service",
            )
        elif response.status_code >= 400:
            # Всегда логируем ошибки клиента
            logger.warning(
                "Request failed with client error",
                method=request.method,
                path=path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                service="graph-service",
            )
        elif should_log:
            # Успешные запросы логируем только для важных путей
            logger.info(
                "Request completed successfully",
                method=request.method,
                path=path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                service="graph-service",
            )

        return response

    except Exception as e:
        # Вычисляем время обработки до момента ошибки
        process_time = time.perf_counter() - start_time

        # Всегда логируем исключения
        logger.exception(
            "Request failed with exception",
            method=request.method,
            path=path,
            error_type=type(e).__name__,
            error_message=str(e),
            process_time_ms=round(process_time * 1000, 2),
            service="graph-service",
        )

        # Пробрасываем исключение дальше для обработки FastAPI
        raise
