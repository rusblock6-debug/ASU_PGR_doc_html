"""Support resolving FastAPI-style dependencies for MQTT callbacks."""

import inspect
from collections.abc import Callable, Sequence
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
)
from typing import Any

from fastapi import params

_MISSING = object()


class DependencyResolver:
    """Resolve FastAPI-style Depends for MQTT handlers."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()

    async def aclose(self) -> None:
        """Close any managed dependency contexts."""
        await self._stack.aclose()

    async def call(self, func: Callable[..., Any], provided_args: Sequence[Any]) -> Any:
        """Execute ``func`` with provided positional data and resolved dependencies."""
        args, kwargs = await self._gather_arguments(func, provided_args)
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def _gather_arguments(
        self,
        func: Callable[..., Any],
        provided_args: Sequence[Any],
    ) -> tuple[list[Any], dict[str, Any]]:
        signature = inspect.signature(func)
        args: list[Any] = []
        kwargs: dict[str, Any] = {}
        provided_iter = iter(provided_args)

        for param in signature.parameters.values():
            if isinstance(param.default, params.Depends):
                kwargs[param.name] = await self._resolve_dependant(param.default)
                continue

            if param.kind is inspect.Parameter.VAR_POSITIONAL:
                args.extend(list(provided_iter))
                continue
            if param.kind is inspect.Parameter.VAR_KEYWORD:
                continue

            value = self._next_value(param, provided_iter)
            if value is _MISSING:
                continue

            if param.kind is inspect.Parameter.KEYWORD_ONLY:
                kwargs[param.name] = value
            else:
                args.append(value)

        return args, kwargs

    async def _resolve_dependant(self, dependant: params.Depends) -> Any:
        dependency = dependant.dependency
        if dependency is None:
            msg = "Depends dependency is not set"
            raise RuntimeError(msg)

        if isinstance(dependency, AbstractAsyncContextManager):
            return await self._stack.enter_async_context(dependency)
        if isinstance(dependency, AbstractContextManager):
            return self._stack.enter_context(dependency)

        return await self._call_dependency(dependency)

    async def _call_dependency(self, dependency: Callable[..., Any]) -> Any:
        args, kwargs = await self._gather_arguments(dependency, [])
        result = dependency(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    @staticmethod
    def _next_value(param: inspect.Parameter, iterator: Any) -> Any:
        try:
            return next(iterator)
        except StopIteration:
            if param.default is inspect._empty:
                msg = f"Missing value for parameter '{param.name}'"
                raise RuntimeError(msg) from None
            return _MISSING
