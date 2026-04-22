"""Middleware for the API gateway."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from aiohttp import ClientError, ClientSession, web
from yarl import URL

from src.config import Settings

_REQUEST_ID_HEADER = "X-Request-Id"
_AUTHORIZATION_HEADER = "Authorization"
_ACCEPT_HEADER = "Accept"
_CONNECTION_HEADER = "Connection"
_UPGRADE_HEADER = "Upgrade"
_USER_AGENT_HEADER = "User-Agent"
_X_FORWARDED_FOR_HEADER = "X-Forwarded-For"
_PROXY_PROTOCOL_KEY = "proxy_protocol"
_UNKNOWN_VALUE = "unknown"
_UNRESOLVED_UPSTREAM = "unresolved"
_HTTP_PROTOCOL = "http"
_SSE_PROTOCOL = "sse"
_WEBSOCKET_PROTOCOL = "websocket"

_Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]

_SKIP_AUTH_PATHS = frozenset({"/health", "/"})
_API_VERSION_PATTERN = re.compile(r"^/api/(?P<version>v[^/]+)(?:/|$)")

logger = logging.getLogger(__name__)


def _extract_api_version(request: web.Request) -> str:
    """Resolve API version from request context or URL path."""
    api_version = request.get("api_version")
    if isinstance(api_version, str) and api_version:
        return api_version

    route_api_version = request.match_info.get("version")
    if route_api_version:
        return route_api_version

    version_match = _API_VERSION_PATTERN.match(request.path)
    if version_match:
        return version_match.group("version")

    return _UNKNOWN_VALUE


def _extract_client_ip(request: web.Request) -> str:
    """Resolve client IP from X-Forwarded-For or aiohttp remote."""
    forwarded_for = request.headers.get(_X_FORWARDED_FOR_HEADER, "")
    if forwarded_for:
        forwarded_ip = forwarded_for.split(",", 1)[0].strip()
        if forwarded_ip:
            return forwarded_ip

    if request.remote:
        return request.remote

    return _UNKNOWN_VALUE


def _extract_response_size(response: web.StreamResponse) -> int:
    """Extract response size in bytes, returning 0 when unknown."""
    content_length = response.content_length
    if content_length is not None and content_length >= 0:
        return int(content_length)

    body_length = response.body_length
    if body_length is not None and body_length >= 0:
        return int(body_length)

    if isinstance(response, web.Response):
        response_body = response.body
        if isinstance(response_body, bytes):
            return len(response_body)

    return 0


def _resolve_error_type(
    request: web.Request,
    status: int,
    error: Exception | None,
) -> str:
    """Resolve a stable error type for error responses."""
    explicit_error_type = request.get("error_type")
    if isinstance(explicit_error_type, str) and explicit_error_type:
        return explicit_error_type

    if error is None and status < 400:
        return "none"

    if isinstance(error, ClientError):
        return "upstream_connection_error"

    if status == 401:
        return "unauthorized"
    if status == 502:
        return "bad_gateway"
    if status == 503:
        return "service_unavailable"

    if isinstance(error, web.HTTPException):
        return f"http_{error.status}"
    if error is not None:
        return type(error).__name__.lower()

    return f"http_{status}"


def _resolve_request_field(request: web.Request, field_name: str, fallback: str) -> str:
    """Resolve string field from request context with fallback."""
    field_value = request.get(field_name)
    if isinstance(field_value, str) and field_value:
        return field_value

    match_info_value = request.match_info.get(field_name)
    if match_info_value:
        return match_info_value

    return fallback


def _resolve_proxy_protocol(request: web.Request) -> str:
    """Resolve request protocol for proxy observability context."""
    explicit_protocol = request.get(_PROXY_PROTOCOL_KEY)
    if isinstance(explicit_protocol, str) and explicit_protocol:
        return explicit_protocol

    connection = request.headers.get(_CONNECTION_HEADER, "").lower()
    upgrade = request.headers.get(_UPGRADE_HEADER, "").lower()
    if "upgrade" in connection and upgrade == _WEBSOCKET_PROTOCOL:
        return _WEBSOCKET_PROTOCOL

    accept = request.headers.get(_ACCEPT_HEADER, "").lower()
    if "text/event-stream" in accept:
        return _SSE_PROTOCOL

    return _HTTP_PROTOCOL


@web.middleware
async def request_lifecycle_logging_middleware(
    request: web.Request,
    handler: _Handler,
) -> web.StreamResponse:
    """Emit per-request completion logs with elapsed time and metadata."""
    started_ns = time.perf_counter_ns()
    request["request_started_ns"] = started_ns

    response: web.StreamResponse | None = None
    request_error: Exception | None = None

    try:
        response = await handler(request)
        return response
    except Exception as exc:
        request_error = exc
        raise
    finally:
        elapsed_ms = max(1, (time.perf_counter_ns() - started_ns) // 1_000_000)

        status = 500
        if response is not None:
            status = response.status
        elif isinstance(request_error, web.HTTPException):
            status = request_error.status

        response_size = _extract_response_size(response) if response is not None else 0
        error_type = _resolve_error_type(request, status, request_error)
        request_id = _resolve_request_field(request, "request_id", _UNKNOWN_VALUE)

        log_payload = {
            "request_id": request_id,
            "elapsed_ms": int(elapsed_ms),
            "method": request.method,
            "path": request.path,
            "query": request.query_string,
            "status": status,
            "service": _resolve_request_field(request, "service", _UNKNOWN_VALUE),
            "api_version": _extract_api_version(request),
            "upstream_url": _resolve_request_field(request, "upstream_url", _UNRESOLVED_UPSTREAM),
            "client_ip": _extract_client_ip(request),
            "user_agent": request.headers.get(_USER_AGENT_HEADER, ""),
            "response_size": response_size,
            "error_type": error_type,
            "protocol": _resolve_proxy_protocol(request),
        }

        if status >= 400:
            logger.error("request_failed", extra=log_payload)
        else:
            logger.info("request_completed", extra=log_payload)


@web.middleware
async def jwt_verification_middleware(
    request: web.Request,
    handler: _Handler,
) -> web.StreamResponse:
    """Verify JWT tokens by calling the auth service.

    If the request carries an Authorization header the middleware forwards it
    to the auth service verify endpoint.  A 200 response lets the request
    proceed; any other status results in a 401 returned to the client.  If
    the auth service is unreachable, the gateway returns 503.

    Requests without an Authorization header or targeting excluded paths
    (e.g. ``/health``) are passed through without verification.
    """
    if request.path in _SKIP_AUTH_PATHS:
        return await handler(request)

    auth_header = request.headers.get(_AUTHORIZATION_HEADER)
    if not auth_header:
        return await handler(request)

    settings: Settings = request.app["settings"]
    verify_url = URL(str(settings.auth.url)) / settings.auth.verify_endpoint.lstrip("/")
    request[_PROXY_PROTOCOL_KEY] = _resolve_proxy_protocol(request)
    request["api_version"] = _extract_api_version(request)
    service = request.match_info.get("service")
    if service:
        request["service"] = service

    session: ClientSession = request.app["client_session"]
    try:
        async with session.post(
            verify_url,
            headers={_AUTHORIZATION_HEADER: auth_header},
        ) as resp:
            if resp.status != 200:
                info = await resp.json()
                request["error_type"] = "unauthorized"
                request["upstream_url"] = str(verify_url)
                return web.json_response(
                    {"error": "Unauthorized", "message": info},
                    status=401,
                )
    except ClientError:
        request["error_type"] = "auth_service_unavailable"
        request["upstream_url"] = str(verify_url)
        return web.json_response(
            {"error": "Service Unavailable"},
            status=503,
        )

    return await handler(request)


@web.middleware
async def request_id_middleware(
    request: web.Request,
    handler: _Handler,
) -> web.StreamResponse:
    """Ensure every request has an X-Request-Id header.

    If the incoming request already carries a non-empty X-Request-Id,
    it is preserved. Otherwise a new UUID4 is generated.

    The resolved request-id is stored in ``request["request_id"]`` so
    downstream handlers (e.g. the proxy) can forward it to upstream
    services.  It is also set on the outgoing response.
    """
    request_id = request.headers.get(_REQUEST_ID_HEADER, "").strip()
    if not request_id:
        request_id = str(uuid.uuid4())

    request["request_id"] = request_id

    response = await handler(request)
    response.headers[_REQUEST_ID_HEADER] = request_id
    return response
