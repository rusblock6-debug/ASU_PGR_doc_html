"""Кастомные зависимости для FastAPI приложения."""

from .pagination import get_pagination_params
from .sort import get_sort_params

__all__ = [
    "get_pagination_params",
    "get_sort_params",
]
