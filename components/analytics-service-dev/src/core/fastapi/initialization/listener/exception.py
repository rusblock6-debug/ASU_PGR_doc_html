"""FastAPI core initialization listener exceptions."""

from fastapi import FastAPI, Request
from fastapi.responses import UJSONResponse
from loguru import logger

from src.core.dto.scheme.response.error import ErrorResponse


def init_ujson_for_exception(app_: FastAPI, loguru_logger: bool = True) -> None:
    """Инициализация слушателей для Exception."""

    @app_.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception) -> UJSONResponse:
        status_code, detail = 500, f"{exc.__class__}: {str(exc)}"

        if loguru_logger:
            ctx = getattr(request.state, "log_context", {})
            logger.bind(**ctx).exception(exc)

        return UJSONResponse(
            status_code=status_code,
            content=ErrorResponse(error_code=status_code, detail=detail).model_dump(),
        )
