"""Базовые исключения API (HTTP-ответы с кодом и сообщением)."""

from typing import Any

from starlette import status


class BaseResponseException(Exception):
    """Базовое исключение для всех ответов API с кодом и сообщением."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
        entity_id: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.entity_id = entity_id
