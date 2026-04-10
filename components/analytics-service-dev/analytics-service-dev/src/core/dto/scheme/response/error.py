"""Схемы ответов для ошибок."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Базовая схема ответа."""

    error_code: int
    detail: str
