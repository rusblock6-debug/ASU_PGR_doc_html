"""SDK exception hierarchy for platform_sdk.

All SDK exceptions derive from SDKError. No httpx or pydantic
exceptions should ever leak outside this package boundary.

Hierarchy:
    SDKError
      TransportError
        ConnectError
        SDKTimeoutError
      ResponseError                (HTTP response received, but failure status)
        BadRequestError            (400)
        UnauthorizedError          (401)
        ForbiddenError             (403)
        NotFoundError              (404)
        ConflictError              (409)
        UnprocessableEntityError   (422 — server rejected the payload)
        RateLimitError             (429)
        ServerError                (5xx)
      ResponseParseError           (response received, but body could not be decoded)
"""

from __future__ import annotations

import httpx


class SDKError(Exception):
    """Base exception for all platform_sdk errors."""


# --- Transport errors (network-level, no HTTP response received) ---


class TransportError(SDKError):
    """Network-level failure — no HTTP response was received."""


class ConnectError(TransportError):
    """Connection to the server could not be established."""


class SDKTimeoutError(TransportError):
    """Request timed out before a response was received.

    Named with the SDK prefix to avoid shadowing the built-in TimeoutError.
    """


# --- Response errors (HTTP response received, but indicates failure) ---


class ResponseError(SDKError):
    """HTTP response received but indicates a failure status code."""

    def __init__(self, message: str, status_code: int, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class BadRequestError(ResponseError):
    """HTTP 400 Bad Request."""


class UnauthorizedError(ResponseError):
    """HTTP 401 Unauthorized."""


class ForbiddenError(ResponseError):
    """HTTP 403 Forbidden."""


class NotFoundError(ResponseError):
    """HTTP 404 Not Found."""


class ConflictError(ResponseError):
    """HTTP 409 Conflict."""


class UnprocessableEntityError(ResponseError):
    """HTTP 422 Unprocessable Entity — the server rejected our payload."""


class RateLimitError(ResponseError):
    """HTTP 429 Too Many Requests. Also triggers retry policy."""


class ServerError(ResponseError):
    """HTTP 5xx Server Error."""


# --- Response decoding error (not a server-side failure) ---


class ResponseParseError(SDKError):
    """The server returned a response, but its body could not be decoded.

    Carries the raw response body for diagnostics. Distinct from
    UnprocessableEntityError (422), which means the server rejected
    *our* payload — ResponseParseError means we cannot understand the server's.
    """

    def __init__(self, message: str, status_code: int, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


# --- Error mapper ---

_STATUS_MAP: dict[int, type[ResponseError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def map_http_error(response: httpx.Response) -> ResponseError:
    """Convert an httpx.Response with a failure status code into a domain exception.

    Does NOT raise — returns the exception instance. Caller is responsible for raising.
    Preserves response body for downstream error messages.
    """
    body = ""
    try:
        body = response.text
    except Exception:  # noqa: BLE001, S110
        body = ""

    exc_class = _STATUS_MAP.get(response.status_code, ServerError)
    message = f"HTTP {response.status_code}: {response.url}"
    if body:
        message = f"{message}\n{body}"
    return exc_class(
        message,
        status_code=response.status_code,
        response_body=body,
    )
