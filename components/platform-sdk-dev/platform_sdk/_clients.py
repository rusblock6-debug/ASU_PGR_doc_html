"""Top-level async facade for platform_sdk.

AsyncClients is the single entry point for SDK consumers::

    async with AsyncClients(settings) as clients:
        result = await clients.analytics.get_vehicle_telemetry(root)

The context manager owns the httpx.AsyncClient lifecycle.
Re-entering the same instance or using it outside `async with` raises a clear
RuntimeError instead of failing later with AttributeError.
"""

from __future__ import annotations

from types import TracebackType

import httpx

from platform_sdk._base_client import AsyncBaseClient
from platform_sdk._settings import ClientSettings
from platform_sdk._transport import build_async_client
from platform_sdk.analytics._client import AsyncAnalyticsClient

__all__ = ["AsyncClients"]


class AsyncClients:
    """Async context manager providing access to all SDK service clients.

    Usage::

        settings = ClientSettings(base_url="https://api.example.com")
        async with AsyncClients(settings) as clients:
            result = await clients.analytics.get_vehicle_telemetry(root)
    """

    def __init__(self, settings: ClientSettings) -> None:
        self._settings = settings
        self._http: httpx.AsyncClient | None = None
        self._base: AsyncBaseClient | None = None
        self._analytics: AsyncAnalyticsClient | None = None
        self._entered = False

    async def __aenter__(self) -> AsyncClients:
        if self._entered:
            raise RuntimeError(
                "AsyncClients context is already entered or has been used; "
                "construct a new AsyncClients instance for each `async with` block.",
            )
        self._entered = True
        self._http = build_async_client(self._settings)
        self._base = AsyncBaseClient(self._http, self._settings)
        self._analytics = AsyncAnalyticsClient(self._base)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._http is not None:
            await self._http.aclose()
        self._http = None
        self._base = None
        self._analytics = None

    @property
    def analytics(self) -> AsyncAnalyticsClient:
        """The analytics service client. Available only inside `async with`."""
        if self._analytics is None:
            raise RuntimeError(
                "AsyncClients must be used as `async with AsyncClients(settings) as clients:`",
            )
        return self._analytics
