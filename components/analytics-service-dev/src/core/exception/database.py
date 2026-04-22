# ruff: noqa: D101

"""Кастомные ошибки для database."""

from http import HTTPStatus

from src.core.exception.exception import CustomHTTPException


class FieldException(CustomHTTPException):
    def __init__(self, detail: str = "Unacceptable field."):
        super().__init__(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=detail)


class DuplicateValueException(CustomHTTPException):
    def __init__(self, detail: str = "Duplicate error, value already exists."):
        super().__init__(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=detail)


class MultipleResultsException(CustomHTTPException):
    def __init__(self, detail: str = "Multiple results were found."):
        super().__init__(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=detail)
