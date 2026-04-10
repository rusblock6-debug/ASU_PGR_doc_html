"""UUID helpers used across the library."""

from __future__ import annotations

import secrets
import time
import uuid
from collections.abc import Callable
from importlib import import_module
from typing import cast


def _load_external_uuid7() -> Callable[[], uuid.UUID] | None:
    """Load uuid6.uuid7() if uuid6 is installed."""
    try:
        mod = import_module("uuid6")
    except ModuleNotFoundError:
        return None
    uuid7_fn = getattr(mod, "uuid7", None)
    if uuid7_fn is None or not callable(uuid7_fn):
        return None
    return cast(Callable[[], uuid.UUID], uuid7_fn)


_uuid7_external = _load_external_uuid7()


def _uuid7_fallback() -> uuid.UUID:
    """Generate UUIDv7 per RFC 9562 using timestamp + randomness."""
    unix_ts_ms = (time.time_ns() // 1_000_000) & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)

    value = (
        (unix_ts_ms << 80)
        | (0x7 << 76)  # version 7
        | (rand_a << 64)
        | (0b10 << 62)  # RFC 4122 variant
        | rand_b
    )
    return uuid.UUID(int=value)


def generate_uuid7() -> uuid.UUID:
    """Return a UUIDv7 value generated on the Python side."""
    if _uuid7_external is not None:
        return _uuid7_external()
    return _uuid7_fallback()
