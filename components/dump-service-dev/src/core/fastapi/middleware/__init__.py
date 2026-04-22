"""Кастомные миддлвары для FastAPI."""

# mypy: disable-error-code="attr-defined"

from .logger import LoguruMiddleware
from .sqlalchemy import SQLAlchemyMiddleware

__all__ = ["SQLAlchemyMiddleware", "LoguruMiddleware"]
