"""HTTP, WebSocket, and SSE proxy handler for dynamic service routing."""

import asyncio
import logging
import re

import aiohttp
from aiohttp import ClientSession, WSMsgType, web
from yarl import URL

from src.config import Settings

logger = logging.getLogger(__name__)
_UNKNOWN_VALUE = "unknown"
_UNRESOLVED_UPSTREAM = "unresolved"
_PROXY_PROTOCOL_KEY = "proxy_protocol"
_HTTP_PROTOCOL = "http"
_SSE_PROTOCOL = "sse"
_WEBSOCKET_PROTOCOL = "websocket"
_API_VERSION_PATTERN = re.compile(r"^/api/(?P<version>v[^/]+)(?:/|$)")
_SUPPORTED_API_VERSIONS = frozenset({"v1", "v2"})


def _extract_api_version(request: web.Request) -> str:
    """Resolve API version from route match or request path."""
    route_api_version = request.match_info.get("version")
    if route_api_version:
        return route_api_version

    version_match = _API_VERSION_PATTERN.match(request.path)
    if version_match:
        return version_match.group("version")

    return _UNKNOWN_VALUE


def _is_sse_request(request: web.Request) -> bool:
    """Check if the request expects an SSE stream."""
    accept = request.headers.get("Accept", "")
    return "text/event-stream" in accept


def _is_sse_response(content_type: str) -> bool:
    """Check if the upstream response is an SSE stream."""
    return "text/event-stream" in content_type


def _is_websocket_upgrade(request: web.Request) -> bool:
    """Check if the request is a WebSocket upgrade request."""
    connection = request.headers.get("Connection", "").lower()
    upgrade = request.headers.get("Upgrade", "").lower()
    return "upgrade" in connection and upgrade == "websocket"


def _build_upstream_url(
    service_url: str,
    api_version: str,
    path_pattern: str,
    path: str,
    query_string: str,
) -> URL:
    """Build the upstream URL from service URL, path pattern, and query string."""
    relative_path = path.lstrip("/")
    pattern_contains_path = "{path}" in path_pattern
    upstream_path = path_pattern.replace("{version}", api_version).replace("{path}", relative_path)

    if pattern_contains_path and not relative_path:
        # Avoid trailing slash artifacts when {path} is empty.
        upstream_path = re.sub(r"/+", "/", upstream_path).rstrip("/") or "/"

    if not pattern_contains_path and relative_path:
        upstream_path = f"{upstream_path.rstrip('/')}/{relative_path}"

    upstream_url = URL(service_url).with_path(upstream_path)
    if query_string:
        upstream_url = upstream_url.with_query(query_string)
    return upstream_url


def _build_upstream_headers(request: web.Request, upstream_url: URL) -> dict[str, str]:
    """Build headers to forward to upstream, setting Host and X-Request-Id."""
    headers = dict(request.headers)
    headers["Host"] = upstream_url.host or ""
    headers.pop("Transfer-Encoding", None)

    request_id: str | None = request.get("request_id")
    if request_id:
        headers["X-Request-Id"] = request_id

    headers["X-Source"] = "api-gateway"

    return headers


def _resolve_context_field(request: web.Request, field_name: str, fallback: str) -> str:
    """Resolve string context values from request and route match."""
    request_value = request.get(field_name)
    if isinstance(request_value, str) and request_value:
        return request_value

    route_value = request.match_info.get(field_name)
    if route_value:
        return route_value

    return fallback


def _proxy_error_log_payload(
    request: web.Request,
    *,
    upstream_url: URL | None,
    error_type: str,
    protocol: str,
    error: Exception,
) -> dict[str, str]:
    """Build structured proxy error log payload without sensitive headers."""
    return {
        "request_id": _resolve_context_field(request, "request_id", _UNKNOWN_VALUE),
        "method": request.method,
        "path": request.path,
        "query": request.query_string,
        "service": _resolve_context_field(request, "service", _UNKNOWN_VALUE),
        "api_version": _resolve_context_field(
            request,
            "api_version",
            _extract_api_version(request),
        ),
        "upstream_url": str(upstream_url) if upstream_url is not None else _UNRESOLVED_UPSTREAM,
        "error_type": error_type,
        "protocol": protocol,
        "exception_type": type(error).__name__,
    }


async def _pipe_ws_client_to_upstream(
    client_ws: web.WebSocketResponse,
    upstream_ws: aiohttp.ClientWebSocketResponse,
) -> None:
    """Forward frames from client WebSocket to upstream WebSocket."""
    async for msg in client_ws:
        if msg.type == WSMsgType.TEXT:
            await upstream_ws.send_str(msg.data)
        elif msg.type == WSMsgType.BINARY:
            await upstream_ws.send_bytes(msg.data)
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            await upstream_ws.close()
            break
        elif msg.type == WSMsgType.ERROR:
            break


async def _pipe_ws_upstream_to_client(
    upstream_ws: aiohttp.ClientWebSocketResponse,
    client_ws: web.WebSocketResponse,
) -> None:
    """Forward frames from upstream WebSocket to client WebSocket."""
    async for msg in upstream_ws:
        if msg.type == WSMsgType.TEXT:
            await client_ws.send_str(msg.data)
        elif msg.type == WSMsgType.BINARY:
            await client_ws.send_bytes(msg.data)
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            await client_ws.close()
            break
        elif msg.type == WSMsgType.ERROR:
            break


async def _handle_websocket(
    request: web.Request,
    upstream_url: URL,
    headers: dict[str, str],
) -> web.WebSocketResponse:
    """Handle a WebSocket upgrade request by proxying to upstream."""
    session: ClientSession = request.app["client_session"]
    request[_PROXY_PROTOCOL_KEY] = _WEBSOCKET_PROTOCOL

    # Remove hop-by-hop headers that should not be forwarded to upstream WS
    ws_headers = {
        k: v
        for k, v in headers.items()
        if k.lower() not in ("connection", "upgrade", "sec-websocket-key", "sec-websocket-version")
    }

    # Convert http(s) URL to ws(s) for the upstream connection
    upstream_ws_url = upstream_url.with_scheme(
        "wss" if upstream_url.scheme == "https" else "ws",
    )

    try:
        upstream_ws = await session.ws_connect(upstream_ws_url, headers=ws_headers)
    except Exception as exc:
        request["error_type"] = "upstream_connection_error"
        logger.error(
            "proxy_websocket_connect_failed",
            extra=_proxy_error_log_payload(
                request,
                upstream_url=upstream_url,
                error_type="upstream_connection_error",
                protocol=_WEBSOCKET_PROTOCOL,
                error=exc,
            ),
        )
        return web.Response(  # type: ignore[return-value]
            status=502,
            text="Failed to connect to upstream WebSocket",
        )

    client_ws = web.WebSocketResponse()
    await client_ws.prepare(request)

    # Bidirectionally pipe frames between client and upstream
    client_to_upstream = asyncio.create_task(
        _pipe_ws_client_to_upstream(client_ws, upstream_ws),
    )
    upstream_to_client = asyncio.create_task(
        _pipe_ws_upstream_to_client(upstream_ws, client_ws),
    )

    try:
        await asyncio.gather(client_to_upstream, upstream_to_client)
    finally:
        client_to_upstream.cancel()
        upstream_to_client.cancel()
        if not upstream_ws.closed:
            await upstream_ws.close()
        if not client_ws.closed:
            await client_ws.close()

    return client_ws


async def _handle_sse(
    request: web.Request,
    upstream_url: URL,
    headers: dict[str, str],
) -> web.StreamResponse:
    """Handle an SSE request by streaming the upstream response to the client."""
    session: ClientSession = request.app["client_session"]
    request[_PROXY_PROTOCOL_KEY] = _SSE_PROTOCOL
    body = await request.read()

    try:
        upstream_resp = await session.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=body if body else None,
        )
    except aiohttp.ClientError as exc:
        request["error_type"] = "upstream_connection_error"
        logger.error(
            "proxy_sse_connect_failed",
            extra=_proxy_error_log_payload(
                request,
                upstream_url=upstream_url,
                error_type="upstream_connection_error",
                protocol=_SSE_PROTOCOL,
                error=exc,
            ),
        )
        return web.json_response({"error": "Bad Gateway"}, status=502)

    try:
        resp_headers = dict(upstream_resp.headers)
        resp_headers.pop("Transfer-Encoding", None)
        resp_headers.pop("Content-Length", None)

        response = web.StreamResponse(
            status=upstream_resp.status,
            headers=resp_headers,
        )
        await response.prepare(request)

        async for chunk in upstream_resp.content.iter_any():
            await response.write(chunk)

        await response.write_eof()
    except ConnectionResetError:
        logger.debug("Client disconnected from SSE stream")
    finally:
        upstream_resp.close()

    return response


async def proxy_handler(request: web.Request) -> web.StreamResponse:
    """Proxy incoming requests to the appropriate upstream service."""
    settings: Settings = request.app["settings"]
    service = request.match_info["service"]
    path = request.match_info.get("path", "")
    api_version = _extract_api_version(request)

    request["service"] = service
    request["api_version"] = api_version
    request[_PROXY_PROTOCOL_KEY] = _HTTP_PROTOCOL
    if _is_websocket_upgrade(request):
        request[_PROXY_PROTOCOL_KEY] = _WEBSOCKET_PROTOCOL
    elif _is_sse_request(request):
        request[_PROXY_PROTOCOL_KEY] = _SSE_PROTOCOL

    service_cfg = settings.services.get(service)
    if service_cfg is None:
        request["upstream_url"] = _UNRESOLVED_UPSTREAM
        request["error_type"] = "service_not_found"
        return web.json_response({"error": "Service not found"}, status=502)

    uses_version = "{version}" in service_cfg.path_pattern
    if uses_version and api_version not in _SUPPORTED_API_VERSIONS:
        request["upstream_url"] = _UNRESOLVED_UPSTREAM
        request["error_type"] = "unsupported_api_version"
        return web.json_response(
            {
                "error": "Unsupported API version",
                "supported_versions": sorted(_SUPPORTED_API_VERSIONS),
            },
            status=400,
        )

    request_version = request.match_info.get("version")
    if request_version and not uses_version:
        request["upstream_url"] = _UNRESOLVED_UPSTREAM
        request["error_type"] = "service_versioning_not_supported"
        logger.warning(
            "proxy_request_rejected_service_without_version_support",
            extra={
                "request_id": _resolve_context_field(request, "request_id", _UNKNOWN_VALUE),
                "method": request.method,
                "path": request.path,
                "service": service,
                "api_version": api_version,
                "path_pattern": service_cfg.path_pattern,
            },
        )
        return web.json_response(
            {
                "error": "Service does not support API versioning",
                "service": service,
            },
            status=400,
        )

    upstream_url = _build_upstream_url(
        str(service_cfg.url),
        api_version,
        service_cfg.path_pattern,
        path,
        request.query_string,
    )
    request["upstream_url"] = str(upstream_url)
    headers = _build_upstream_headers(request, upstream_url)

    # Handle WebSocket upgrade requests
    if _is_websocket_upgrade(request):
        return await _handle_websocket(request, upstream_url, headers)

    # Handle SSE requests (client explicitly asks for event-stream)
    if _is_sse_request(request):
        return await _handle_sse(request, upstream_url, headers)

    # Standard HTTP proxy
    body = await request.read()

    session: ClientSession = request.app["client_session"]
    try:
        async with session.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=body if body else None,
        ) as upstream_resp:
            # If upstream returns SSE even though client didn't ask with Accept header,
            # stream it instead of buffering
            content_type = upstream_resp.headers.get("Content-Type", "")
            if _is_sse_response(content_type):
                request[_PROXY_PROTOCOL_KEY] = _SSE_PROTOCOL
                resp_headers = dict(upstream_resp.headers)
                resp_headers.pop("Transfer-Encoding", None)
                resp_headers.pop("Content-Length", None)

                response = web.StreamResponse(
                    status=upstream_resp.status,
                    headers=resp_headers,
                )
                await response.prepare(request)

                try:
                    async for chunk in upstream_resp.content.iter_any():
                        await response.write(chunk)
                    await response.write_eof()
                except ConnectionResetError:
                    logger.debug("Client disconnected from SSE stream")

                return response

            resp_headers = dict(upstream_resp.headers)
            resp_headers.pop("Transfer-Encoding", None)
            resp_headers.pop("Content-Encoding", None)

            resp_body = await upstream_resp.read()
            return web.Response(
                status=upstream_resp.status,
                headers=resp_headers,
                body=resp_body,
            )
    except aiohttp.ClientError as exc:
        request["error_type"] = "upstream_connection_error"
        logger.error(
            "proxy_http_connect_failed",
            extra=_proxy_error_log_payload(
                request,
                upstream_url=upstream_url,
                error_type="upstream_connection_error",
                protocol=_resolve_context_field(request, _PROXY_PROTOCOL_KEY, _HTTP_PROTOCOL),
                error=exc,
            ),
        )
        return web.json_response({"error": "Bad Gateway"}, status=502)


async def missing_version_handler(request: web.Request) -> web.StreamResponse:
    """Route non-versioned services to the proxy, or return 400 when version is missing."""
    settings: Settings = request.app["settings"]
    service = request.match_info.get("service", _UNKNOWN_VALUE)
    service_cfg = settings.services.get(service)

    if service_cfg is not None and "{version}" not in service_cfg.path_pattern:
        return await proxy_handler(request)

    request["service"] = service
    request["api_version"] = _UNKNOWN_VALUE
    request["upstream_url"] = _UNRESOLVED_UPSTREAM
    request["error_type"] = "missing_api_version"
    return web.json_response(
        {
            "error": "Missing API version segment. Use /api/{version}/{service}/{path}",
        },
        status=400,
    )
