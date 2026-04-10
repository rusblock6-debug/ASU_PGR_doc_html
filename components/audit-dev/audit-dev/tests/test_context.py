"""Tests for audit_lib.context — contextvars-based user/service context."""

from __future__ import annotations

import asyncio

import pytest

from audit_lib.context import (
    get_audit_service,
    get_audit_user,
    set_audit_context,
    set_audit_user,
)

def test_get_audit_user_default_none() -> None:
    """get_audit_user() returns None when no context is set."""
    assert get_audit_user() is None


def test_set_audit_user_sync() -> None:
    """set_audit_user sets user_id inside sync context manager."""
    with set_audit_user("user-42"):
        assert get_audit_user() == "user-42"


def test_set_audit_user_reset_after_exit() -> None:
    """After exiting set_audit_user, get_audit_user returns None."""
    with set_audit_user("user-42"):
        pass
    assert get_audit_user() is None


def test_set_audit_user_nested() -> None:
    """Nested set_audit_user restores outer value on exit."""
    with set_audit_user("outer"):
        assert get_audit_user() == "outer"
        with set_audit_user("inner"):
            assert get_audit_user() == "inner"
        assert get_audit_user() == "outer"
    assert get_audit_user() is None


def test_set_audit_context_sync() -> None:
    """set_audit_context sets both user_id and service_name."""
    with set_audit_context(user_id="user-1", service_name="billing"):
        assert get_audit_user() == "user-1"
        assert get_audit_service() == "billing"
    assert get_audit_user() is None
    assert get_audit_service() is None


def test_set_audit_context_partial_user_only() -> None:
    """set_audit_context with only user_id leaves service_name unchanged."""
    with set_audit_context(user_id="user-1"):
        assert get_audit_user() == "user-1"
        assert get_audit_service() is None


def test_set_audit_context_partial_service_only() -> None:
    """set_audit_context with only service_name leaves user_id unchanged."""
    with set_audit_context(service_name="billing"):
        assert get_audit_user() is None
        assert get_audit_service() == "billing"


def test_get_audit_service_default_none() -> None:
    """get_audit_service() returns None when no context is set."""
    assert get_audit_service() is None


@pytest.mark.asyncio
async def test_set_audit_user_async() -> None:
    """set_audit_user works as async context manager."""
    async with set_audit_user("async-user"):
        assert get_audit_user() == "async-user"
    assert get_audit_user() is None


@pytest.mark.asyncio
async def test_set_audit_context_async() -> None:
    """set_audit_context works as async context manager."""
    async with set_audit_context(user_id="u1", service_name="svc"):
        assert get_audit_user() == "u1"
        assert get_audit_service() == "svc"
    assert get_audit_user() is None
    assert get_audit_service() is None


@pytest.mark.asyncio
async def test_contextvars_isolation_between_coroutines() -> None:
    """Each coroutine gets its own copy of the context variable."""
    results: dict[str, str | None] = {}

    async def worker(name: str, user_id: str) -> None:
        async with set_audit_user(user_id):
            await asyncio.sleep(0.01)  # yield control
            results[name] = get_audit_user()

    await asyncio.gather(
        worker("a", "user-a"),
        worker("b", "user-b"),
    )

    assert results["a"] == "user-a"
    assert results["b"] == "user-b"
    # After all coroutines finish, main context is clean
    assert get_audit_user() is None


@pytest.mark.asyncio
async def test_contextvars_isolation_no_leak() -> None:
    """Setting context in one coroutine does not leak to another."""
    barrier = asyncio.Event()
    seen_by_observer: str | None = "SENTINEL"

    async def setter() -> None:
        async with set_audit_user("leaked?"):
            barrier.set()
            await asyncio.sleep(0.05)

    async def observer() -> None:
        nonlocal seen_by_observer
        await barrier.wait()
        seen_by_observer = get_audit_user()

    await asyncio.gather(setter(), observer())
    assert seen_by_observer is None
