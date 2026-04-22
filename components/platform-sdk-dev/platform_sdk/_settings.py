"""Centralized SDK configuration using pydantic v2.

ClientSettings is frozen (immutable after construction) to prevent
accidental mutation of shared config across concurrent requests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class TimeoutSettings(BaseModel):
    """Per-phase HTTP timeout configuration in seconds."""

    connect: float = 5.0
    read: float = 30.0
    write: float = 10.0
    pool: float = 5.0


class RetrySettings(BaseModel):
    """Retry policy configuration for the transport layer."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    max_wait: float = Field(default=60.0, gt=0)


@dataclass(frozen=True)
class RetryEvent:
    """Information about a single retry attempt, passed to the on_retry callback."""

    attempt: int
    """1-based number of the attempt that just failed (next attempt is attempt + 1)."""

    method: str
    url: str
    request_id: str

    sleep_seconds: float
    """Backoff duration before the next attempt."""

    exception: BaseException
    """The exception that triggered the retry (httpx.TransportError or httpx.HTTPStatusError)."""


OnRetry = Callable[[RetryEvent], None]


class ClientSettings(BaseModel):
    """Top-level SDK configuration. Immutable after construction (frozen=True).

    Args:
        base_url: Base URL for all requests. Must be a valid HTTP/HTTPS URL.
        timeout: Per-phase timeout settings (connect, read, write, pool).
        retry: Retry policy (max_attempts, max_wait for exponential backoff).
        headers: Default headers added to every request.
        verify_ssl: Whether to verify TLS certificates. Default True.
        on_retry: Optional synchronous callback invoked on every retry attempt.
                  Use it to count retries, push metrics or attach extra logging.
                  Exceptions raised inside the callback are swallowed and logged.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    base_url: AnyHttpUrl
    timeout: TimeoutSettings = Field(default_factory=TimeoutSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    headers: dict[str, str] = Field(default_factory=dict)
    verify_ssl: bool = True
    on_retry: OnRetry | None = None
