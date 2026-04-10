"""Custom KeyMaker."""

# ruff: noqa: D101
# mypy: disable-error-code="no-untyped-def,type-arg,union-attr"

import inspect
from collections.abc import Callable
from typing import Any


class FunctionKeyMaker:
    def __init__(self) -> None:
        self.project_name: str | None = None

    def _set_project_name(self, project_name: str) -> None:
        self.project_name = project_name

    async def make_key(self, function: Callable, *args, **kwargs) -> str:
        """Make key with prefix, module and func."""
        if self.project_name is None:
            raise Exception("project_name не задан")
        key = f"{self.project_name}|"

        # Создаем словарь имен и значений параметров
        bound_args = inspect.signature(function).bind(*args, **kwargs)
        bound_args.apply_defaults()
        function_params = ",".join(
            self.make_function_param(name=name, value=value)
            for name, value in bound_args.arguments.items()
        )
        key += f"({function_params})::"

        key += f"{inspect.getmodule(function).__name__}.{function.__name__}"
        return key

    async def make_invalid_mask_key(self, function: Callable) -> str:
        """Создать ключ-маску для инвалидации."""
        if self.project_name is None:
            raise Exception("project_name не задан")
        key = f"{self.project_name}|"
        key += "(*)::"

        key += f"{inspect.getmodule(function).__name__}.{function.__name__}"
        return key

    @staticmethod
    def make_function_param(name: str, value: Any) -> str:
        """Метод создания ключа для параметра функции."""
        return f"{name}={repr(value)}"
