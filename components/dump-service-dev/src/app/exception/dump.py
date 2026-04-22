# ruff: noqa: D100, D101

"""Кастомные ошибки для приложения."""

from http import HTTPStatus

from src.core.exception.exception import CustomHTTPException


class DumpIsAlreadyGenerated(CustomHTTPException):
    def __init__(self, detail: str = "Dump is already generated"):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=detail)


class DumpCanNotBeEmpty(CustomHTTPException):
    def __init__(self, detail: str = "Dump cannot be empty"):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=detail)
