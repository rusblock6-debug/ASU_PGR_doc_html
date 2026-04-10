"""Исключения сервера (5xx)."""

from starlette import status

from app.api.exceptions.base import BaseResponseException


class ServerErrorException(BaseResponseException):
    """Внутренняя ошибка сервера (500)."""

    def __init__(self, message: str | None = None):
        super().__init__(
            message=message if message is not None else "Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="SERVER_ERROR",
        )
