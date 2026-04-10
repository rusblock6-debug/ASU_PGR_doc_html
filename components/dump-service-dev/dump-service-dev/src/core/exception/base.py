# ruff: noqa: D101

"""Кастомные ошибки для handler и responses."""

from http import HTTPStatus

from src.core.exception.exception import CustomHTTPException


class InternalServerException(CustomHTTPException):
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=detail)


class BadRequestException(CustomHTTPException):
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=detail)


class NotFoundException(CustomHTTPException):
    def __init__(self, detail: str = "Not found"):
        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=detail)


class UnprocessableEntityException(CustomHTTPException):
    def __init__(self, detail: str = "Unprocessable entity"):
        super().__init__(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=detail)


class PayloadTooLargeException(CustomHTTPException):
    def __init__(self, message: str = "Payload too large"):
        super().__init__(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            detail=message,
        )


class UnsupportedMediaTypeException(CustomHTTPException):
    def __init__(self, message: str = "Unsupported media type"):
        super().__init__(status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE, detail=message)


class TooEarlyException(CustomHTTPException):
    def __init__(self, message: str = "Too early"):
        super().__init__(status_code=HTTPStatus.TOO_EARLY, detail=message)
