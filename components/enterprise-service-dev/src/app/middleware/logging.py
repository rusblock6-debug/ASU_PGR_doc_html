"""Middleware для логирования HTTP-запросов и ответов."""

import sys
import time
import traceback
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from loguru import logger

# Пути, которые не нужно логировать на уровне info (только ошибки)
SKIP_INFO_LOGGING = [
    "/health",
    "/healthcheck",
    "/metrics",
    "/favicon.ico",
    "/ws/",
    "/docs",
    "/redoc",
    "/openapi.json",
]


def _should_log_request(path: str) -> bool:
    """Проверить, нужно ли логировать запрос на уровне info."""
    return not any(path.startswith(skip_path) for skip_path in SKIP_INFO_LOGGING)


async def log_requests_middleware(
    request: Request,
    call_next: Callable[[Request], Coroutine[Any, Any, Response]],
) -> Response:
    """Middleware для логирования всех HTTP-запросов и ответов, включая ошибки.

    Служебные запросы (health, docs) логируются только при ошибках.
    """
    start_time = time.perf_counter()

    # Логируем входящий запрос
    logger.info(
        "Incoming request",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_host=request.client.host if request.client else None,
    )

    try:
        # Обрабатываем запрос
        response = await call_next(request)

        # Вычисляем время обработки
        process_time = time.perf_counter() - start_time

        # Логируем ответ в зависимости от статуса
        if response.status_code >= 500:
            logger.error(
                "Request failed with server error",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )
        elif response.status_code >= 400:
            logger.warning(
                "Request failed with client error",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )
        else:
            logger.info(
                "Request completed successfully",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )

        return response

    except Exception as e:
        # Вычисляем время обработки до момента ошибки
        process_time = time.perf_counter() - start_time

        # Извлекаем информацию о последнем кадре стека (где произошла ошибка)
        tb = sys.exc_info()[2]
        if tb:
            # Получаем информацию о последнем кадре
            filename, lineno, funcname, line = traceback.extract_tb(tb)[-1]
            pathname = filename
        else:
            pathname = "unknown"
            lineno = 0
            funcname = "unknown"

        # Логируем исключение с полным traceback
        logger.exception(
            "Request failed with exception",
            method=request.method,
            path=request.url.path,
            error_type=type(e).__name__,
            error_message=str(e),
            process_time_ms=round(process_time * 1000, 2),
            pathname=pathname,
            lineno=lineno,
            funcname=funcname,
        )

        # Пробрасываем исключение дальше для обработки FastAPI
        raise
