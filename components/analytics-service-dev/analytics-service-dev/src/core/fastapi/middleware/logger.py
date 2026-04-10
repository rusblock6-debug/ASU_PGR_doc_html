# ruff: noqa: D101
"""Middleware для логирования запроса-ответа от сервиса."""

import time
from uuid import uuid4

from fastapi import Request
from loguru import logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.core.dto.scheme.response.error import ErrorResponse


class LoguruMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app_ = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Logger middleware."""
        if scope["type"] not in ("http", "https"):
            await self.app_(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = request.headers.get("X-Request-Id", str(uuid4()))
        xff = request.headers.get("X-Original-Forwarded-For", "").split(",")
        if len(xff) > 0:
            request_ip = xff[0]
        elif request.client:
            request_ip = request.client.host
        else:
            request_ip = "unknown"
        request_body_size = int(request.headers.get("Content-Length", 0))
        request_method = request.method
        request_path = request.url.path
        request_query = request.url.query

        request.state.log_context = {
            "request_id": request_id,
            "request_ip": request_ip,
            "request_method": request_method,
            "request_path": request_path,
            "request_query": request_query,
            "request_body_size": request_body_size,
        }

        # Контекст, который будет добавлен во все лог-вызовы ниже
        with logger.contextualize(
            request_id=request_id,
            request_ip=request_ip,
            request_method=request_method,
            request_path=request_path,
            request_query=request_query,
            request_body_size=request_body_size,
        ):
            logger.info("Incoming request")

            start = time.perf_counter()
            response_status = 500
            response_size = 0
            error_body = bytearray()

            async def send_wrapper(message: Message) -> None:
                nonlocal response_status, response_size, error_body
                m_type = message.get("type", "")
                if m_type.endswith(".response.start"):
                    response_status = message["status"]
                elif m_type.endswith(".response.body"):
                    body = message.get("body", b"")
                    response_size += len(body)
                    if 200 < response_status < 500:
                        error_body.extend(body)
                await send(message)

            try:
                await self.app_(scope, receive, send_wrapper)
            finally:
                elapsed = time.perf_counter() - start
                log_args = dict(
                    status_code=response_status,
                    processing_time=f"{elapsed:.4f}",
                    response_body_size=response_size,
                )
                if response_status < 500:
                    if response_status != 200:
                        try:
                            error_response = ErrorResponse.model_validate_json(
                                error_body,
                            )
                            log_args["error_message"] = error_response.detail
                        except Exception as exc:
                            logger.warning(f"failed to validate error response: {exc}")
                    logger.info("Success response", **log_args)
