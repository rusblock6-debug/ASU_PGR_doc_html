"""Кастомные миддлвары для FastAPI."""

# mypy: disable-error-code="attr-defined"

from .logger import LoguruMiddleware

__all__ = ["LoguruMiddleware"]
