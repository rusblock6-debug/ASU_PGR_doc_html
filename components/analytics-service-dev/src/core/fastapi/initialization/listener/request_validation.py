"""Слушатели для RequestValidationError."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import UJSONResponse

from src.core.dto.scheme.response.error import ErrorResponse


def init_ujson_for_request_validation_error(app_: FastAPI) -> None:
    """Инициализация слушателя для RequestValidationError."""

    @app_.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> UJSONResponse:
        errors = exc.errors()
        detail = "; ".join(
            f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg', '')}" for e in errors
        )
        return UJSONResponse(
            status_code=422,
            content=ErrorResponse(error_code=422, detail=detail).model_dump(),
        )
