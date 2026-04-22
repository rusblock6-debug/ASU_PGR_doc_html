"""Модуль кастомных exception."""

from .auth import ForbiddenException, UnauthorizedException
from .base import (
    BadRequestException,
    InternalServerException,
    NotFoundException,
    PayloadTooLargeException,
    TooEarlyException,
    UnprocessableEntityException,
    UnsupportedMediaTypeException,
)
from .database import DuplicateValueException, FieldException, MultipleResultsException

__all__ = [
    "FieldException",
    "InternalServerException",
    "BadRequestException",
    "NotFoundException",
    "ForbiddenException",
    "UnauthorizedException",
    "UnprocessableEntityException",
    "DuplicateValueException",
    "PayloadTooLargeException",
    "TooEarlyException",
    "UnsupportedMediaTypeException",
    "MultipleResultsException",
]
