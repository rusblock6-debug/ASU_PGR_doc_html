"""Contextvars-based audit context for user_id and service_name binding."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

audit_user_var: ContextVar[str | None] = ContextVar("audit_user", default=None)
audit_service_var: ContextVar[str | None] = ContextVar(
    "audit_service", default=None
)


def get_audit_user() -> str | None:
    """Return the current audit user_id, or None if not set."""
    return audit_user_var.get()


def get_audit_service() -> str | None:
    """Return the current audit service_name, or None if not set."""
    return audit_service_var.get()


class set_audit_user:  # noqa: N801
    """Context manager that sets audit user_id for the current scope.

    Works as both sync and async context manager::

        with set_audit_user("user-42"):
            assert get_audit_user() == "user-42"

        async with set_audit_user("user-42"):
            assert get_audit_user() == "user-42"
    """

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._token: Token[str | None] | None = None

    def __enter__(self) -> set_audit_user:
        self._token = audit_user_var.set(self._user_id)
        return self

    def __exit__(self, *_args: Any) -> None:
        if self._token is not None:
            audit_user_var.reset(self._token)
            self._token = None

    async def __aenter__(self) -> set_audit_user:
        return self.__enter__()

    async def __aexit__(self, *_args: Any) -> None:
        self.__exit__()


class set_audit_context:  # noqa: N801
    """Context manager that sets both user_id and service_name.

    Works as both sync and async context manager::

        with set_audit_context(user_id="user-42", service_name="billing"):
            assert get_audit_user() == "user-42"
            assert get_audit_service() == "billing"
    """

    def __init__(
        self,
        user_id: str | None = None,
        service_name: str | None = None,
    ) -> None:
        self._user_id = user_id
        self._service_name = service_name
        self._user_token: Token[str | None] | None = None
        self._service_token: Token[str | None] | None = None

    def __enter__(self) -> set_audit_context:
        if self._user_id is not None:
            self._user_token = audit_user_var.set(self._user_id)
        if self._service_name is not None:
            self._service_token = audit_service_var.set(self._service_name)
        return self

    def __exit__(self, *_args: Any) -> None:
        if self._user_token is not None:
            audit_user_var.reset(self._user_token)
            self._user_token = None
        if self._service_token is not None:
            audit_service_var.reset(self._service_token)
            self._service_token = None

    async def __aenter__(self) -> set_audit_context:
        return self.__enter__()

    async def __aexit__(self, *_args: Any) -> None:
        self.__exit__()
