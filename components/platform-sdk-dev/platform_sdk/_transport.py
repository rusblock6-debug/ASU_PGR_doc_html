"""Transport layer for platform_sdk.

Provides:
- build_async_client(): httpx.AsyncClient factory with connection pooling
- execute_with_retry(): retry-aware request executor with jitter backoff
- generate_request_id(): UUID4-based request ID for X-Request-ID header
- _mask_headers(): sensitive header value masking for structured logging

This module does NOT import from _exceptions — it raises raw httpx errors.
Exception wrapping is the base client's responsibility.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from platform_sdk._settings import ClientSettings, OnRetry, RetryEvent

logger = logging.getLogger("platform_sdk.transport")

# Status codes that trigger retry. 4xx business errors are NOT in this set.
# 429 = Rate Limit (also retried), 500/502/503/504 = server-side failures.
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

REQUEST_ID_HEADER: str = "X-Request-ID"

# Headers whose values must never appear in logs.
_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {
        "authorization",
        "x-api-key",
        "cookie",
        "set-cookie",
        "proxy-authorization",
    },
)


def build_async_client(settings: ClientSettings) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient configured from ClientSettings.

    The caller owns the client lifecycle — call await client.aclose() when done.
    In production, AsyncClients context manager handles this.

    Connection pool defaults:
      max_keepalive_connections=20, max_connections=100, keepalive_expiry=30s
    """
    timeout = httpx.Timeout(
        connect=settings.timeout.connect,
        read=settings.timeout.read,
        write=settings.timeout.write,
        pool=settings.timeout.pool,
    )
    limits = httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30.0,
    )
    return httpx.AsyncClient(
        base_url=str(settings.base_url),
        timeout=timeout,
        limits=limits,
        headers=settings.headers,
        verify=settings.verify_ssl,
    )


def generate_request_id() -> str:
    """Return a new UUID4 string for use as X-Request-ID / X-Correlation-ID."""
    return str(uuid.uuid4())


def _mask_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive values replaced by ***REDACTED***.

    Matching is case-insensitive. The original dict is not modified.
    """
    return {k: "***REDACTED***" if k.lower() in _SENSITIVE_HEADERS else v for k, v in headers.items()}


def _is_retryable(exc: BaseException) -> bool:
    """Predicate for tenacity: True if the exception warrants a retry attempt."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return False


def _build_before_sleep(
    *,
    method: str,
    url: str,
    request_id: str,
    on_retry: OnRetry | None,
) -> Callable[[RetryCallState], None]:
    """Construct a before_sleep callback for AsyncRetrying.

    Logs every retry at WARNING and forwards a structured RetryEvent
    to the user-supplied callback when one is configured.
    """

    def _callback(state: RetryCallState) -> None:
        outcome = state.outcome
        if outcome is None or not outcome.failed:
            return
        exc = outcome.exception()
        if exc is None:
            return
        sleep_seconds = float(state.next_action.sleep) if state.next_action is not None else 0.0
        reason = _describe_exception(exc)

        logger.warning(
            "HTTP request retrying",
            extra={
                "method": method,
                "url": url,
                "attempt": state.attempt_number,
                "sleep_seconds": round(sleep_seconds, 3),
                "reason": reason,
                "request_id": request_id,
            },
        )

        if on_retry is None:
            return
        event = RetryEvent(
            attempt=state.attempt_number,
            method=method,
            url=url,
            request_id=request_id,
            sleep_seconds=sleep_seconds,
            exception=exc,
        )
        try:
            on_retry(event)
        except Exception:  # noqa: BLE001 — callback errors must not break the request
            logger.exception("on_retry callback raised", extra={"request_id": request_id})

    return _callback


def _describe_exception(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"status={exc.response.status_code}"
    return f"{type(exc).__name__}: {exc}"


async def execute_with_retry(
    coro_factory: Callable[[], Coroutine[Any, Any, httpx.Response]],
    *,
    method: str,
    url: str,
    request_headers: dict[str, str] | None = None,
    request_id: str,
    max_attempts: int = 3,
    max_wait: float = 60.0,
    on_retry: OnRetry | None = None,
) -> httpx.Response:
    """Execute an HTTP request coroutine with exponential backoff retry.

    Args:
        coro_factory: Callable that returns a fresh coroutine for each attempt.
                      Must be a factory (called per attempt) not a single coroutine.
        method: HTTP method string for logging (e.g. "GET", "POST").
        url: Full URL string for logging.
        request_headers: Request headers for logging (values are masked).
        request_id: Request id used for log correlation. Caller is responsible for
            also placing the same value into the outgoing X-Request-ID header.
        max_attempts: Maximum number of attempts including the first. Default 3.
        max_wait: Maximum seconds to wait between retries. Default 60.0.
        on_retry: Optional callback invoked before each retry sleep.

    Returns:
        httpx.Response on success.

    Raises:
        httpx.HTTPStatusError: Re-raised after max_attempts for retryable status codes.
        httpx.TransportError: Re-raised after max_attempts for network errors.
        Any exception raised by coro_factory that is not retryable: raised immediately.
    """
    safe_headers = _mask_headers(request_headers or {})
    start = time.monotonic()

    async def _attempt_once() -> httpx.Response:
        resp = await coro_factory()
        if resp.status_code in RETRYABLE_STATUS_CODES:
            # Surface as HTTPStatusError so tenacity (and on_retry) see it.
            resp.raise_for_status()
        return resp

    async for attempt in AsyncRetrying(
        retry=retry_if_exception(_is_retryable),
        wait=wait_random_exponential(multiplier=1, max=max_wait),
        stop=stop_after_attempt(max_attempts),
        before_sleep=_build_before_sleep(
            method=method,
            url=url,
            request_id=request_id,
            on_retry=on_retry,
        ),
        reraise=True,
    ):
        with attempt:
            response = await _attempt_once()

    duration_ms = round((time.monotonic() - start) * 1000, 2)
    logger.info(
        "HTTP request completed",
        extra={
            "method": method,
            "url": url,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "headers": safe_headers,
        },
    )
    return response
