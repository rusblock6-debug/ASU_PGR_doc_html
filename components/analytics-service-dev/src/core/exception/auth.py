# ruff: noqa: D100, D101

from http import HTTPStatus

from src.core.exception.exception import CustomHTTPException


class ForbiddenException(CustomHTTPException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=HTTPStatus.FORBIDDEN, detail=detail)


class UnauthorizedException(CustomHTTPException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=HTTPStatus.UNAUTHORIZED, detail=detail)
