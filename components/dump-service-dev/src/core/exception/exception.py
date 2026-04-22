# ruff: noqa: D100

from http.client import HTTPException
from typing import Any

from src.core.dto.scheme.response.error import ErrorResponse


class CustomHTTPException(HTTPException):
    """Родитель кастомного HTTP исключения."""

    def __init__(self, status_code: int, detail: str = "Server error"):
        self.status_code = status_code
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        """Представление ошибки как dict."""
        return ErrorResponse(
            error_code=self.status_code,
            detail=self.detail,
        ).model_dump()

    def as_response(self) -> ErrorResponse:
        """Представление ошибки как ErrorResponse схема."""
        return ErrorResponse(error_code=self.status_code, detail=self.detail)
