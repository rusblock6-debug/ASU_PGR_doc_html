"""Модуль для слушателей при инициализации FastAPI."""

from .custom_http_exception import init_ujson_for_custom_http_exception
from .exception import init_ujson_for_exception
from .request_validation import init_ujson_for_request_validation_error

__all__ = [
    "init_ujson_for_custom_http_exception",
    "init_ujson_for_exception",
    "init_ujson_for_request_validation_error",
]
