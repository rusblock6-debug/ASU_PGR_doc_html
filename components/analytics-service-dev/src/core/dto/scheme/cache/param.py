# mypy: disable-error-code="no-any-return"
# ruff: noqa: I001
"""Схема параметров для декоратора инвалидации кеша."""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict


class ConvertParam(BaseModel):
    """Схема конвертации параметров для инвалидации."""

    wrapped_func_param: str
    caching_func_param: str | None = None


class CacheInvalidateParams(BaseModel):
    """Схема инвалидатора."""

    functions: list[Callable]  # type: ignore
    params: list[ConvertParam] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
