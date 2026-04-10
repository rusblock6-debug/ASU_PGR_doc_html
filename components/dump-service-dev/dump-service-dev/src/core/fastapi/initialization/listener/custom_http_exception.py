"""Слушатели для CustomHTTPException."""

from fastapi import FastAPI, Request
from fastapi.responses import UJSONResponse
from loguru import logger

from src.core.exception.exception import CustomHTTPException


def init_ujson_for_custom_http_exception(
    app_: FastAPI,
    loguru_logger: bool = True,
) -> None:
    """Инициализация слушателя для CustomHTTPException."""

    @app_.exception_handler(CustomHTTPException)
    async def custom_http_exception_handler(
        request: Request,
        exc: CustomHTTPException,
    ) -> UJSONResponse:
        if loguru_logger and exc.status_code >= 500:
            ctx = getattr(request.state, "log_context", {})
            logger.bind(**ctx).error(exc.detail)

        return UJSONResponse(status_code=exc.status_code, content=exc.as_dict())
