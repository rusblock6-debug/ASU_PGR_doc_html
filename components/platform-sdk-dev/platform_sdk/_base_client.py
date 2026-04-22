"""Async base client for platform_sdk service clients.

Provides the HTTP request layer with:
- Retry via execute_with_retry (tenacity exponential backoff)
- Per-request timeout and header overrides
- Error boundary: all httpx and pydantic errors wrapped in SDK exceptions
- X-Request-ID injection on every outgoing request

Domain clients (e.g. AsyncAnalyticsClient) compose AsyncBaseClient and
talk to it through the public `request` and `request_model` methods.
"""

from __future__ import annotations

from typing import Any, TypeVar

import httpx
import pydantic

from platform_sdk._exceptions import (
    ConnectError,
    ResponseParseError,
    SDKTimeoutError,
    map_http_error,
)
from platform_sdk._settings import ClientSettings
from platform_sdk._transport import (
    REQUEST_ID_HEADER,
    execute_with_retry,
    generate_request_id,
)

T = TypeVar("T", bound=pydantic.BaseModel)

__all__ = ["AsyncBaseClient"]


class AsyncBaseClient:
    """Base HTTP client for all SDK service clients.

    Accepts an injected httpx.AsyncClient and ClientSettings.
    Does NOT create or close the HTTP client — caller is responsible for lifecycle.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        settings: ClientSettings,
    ) -> None:
        self._http = http_client
        self._settings = settings

    async def request(
        self,
        method: str,
        path: str,
        *,
        timeout: httpx.Timeout | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with retry and error boundary.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: URL path relative to base_url (e.g. "/api/v1/resource").
            timeout: Per-request timeout override. None uses the client default.
            headers: Per-request headers merged over settings.headers (overrides win).
            **kwargs: Additional kwargs forwarded to httpx (json=, params=, content=, etc.)

        Returns:
            httpx.Response with a 2xx status code.

        Raises:
            ResponseError subclass for 4xx/5xx responses.
            SDKTimeoutError for any timeout condition.
            ConnectError for network-level failures.
        """
        request_id = generate_request_id()
        merged_headers: dict[str, str] = {
            **self._settings.headers,
            **(headers or {}),
            REQUEST_ID_HEADER: request_id,
        }
        request_kwargs: dict[str, Any] = {**kwargs, "headers": merged_headers}
        if timeout is not None:
            request_kwargs["timeout"] = timeout

        try:
            response = await execute_with_retry(
                lambda: self._http.request(method, path, **request_kwargs),
                method=method,
                url=path,
                request_headers=merged_headers,
                request_id=request_id,
                max_attempts=self._settings.retry.max_attempts,
                max_wait=self._settings.retry.max_wait,
                on_retry=self._settings.on_retry,
            )
            self._raise_for_status(response)
            return response
        except httpx.HTTPStatusError as exc:
            # Raised by execute_with_retry when retryable status codes
            # exhaust the retry budget.
            raise map_http_error(exc.response) from exc
        except httpx.TimeoutException as exc:
            raise SDKTimeoutError(str(exc)) from exc
        except httpx.TransportError as exc:
            raise ConnectError(str(exc)) from exc

    async def request_model(
        self,
        method: str,
        path: str,
        response_model: type[T],
        *,
        timeout: httpx.Timeout | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute an HTTP request and parse the response into a pydantic model.

        Same arguments as `request` plus `response_model`. The response body
        must decode as JSON matching the model schema, otherwise raises
        ResponseParseError.
        """
        response = await self.request(method, path, timeout=timeout, headers=headers, **kwargs)
        try:
            data = response.json()
            return response_model.model_validate(data)
        except (pydantic.ValidationError, ValueError) as exc:
            raise ResponseParseError(
                f"Failed to decode response into {response_model.__name__}: {exc}",
                status_code=response.status_code,
                response_body=response.text,
            ) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Convert an error HTTP response into an SDK domain exception."""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise map_http_error(exc.response) from exc
