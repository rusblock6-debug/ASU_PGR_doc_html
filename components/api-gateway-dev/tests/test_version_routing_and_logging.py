"""Integration tests for version routing and structured request logs."""

import json
import logging
import unittest
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from src.app import create_app
from src.config import Settings
from src.logging_setup import JsonFormatter

_REQUEST_LOG_KEYS = {
    "timestamp",
    "level",
    "message",
    "request_id",
    "elapsed_ms",
    "method",
    "path",
    "query",
    "status",
    "service",
    "api_version",
    "upstream_url",
    "client_ip",
    "user_agent",
    "response_size",
    "error_type",
}


class _CaptureHandler(logging.Handler):
    """Collect emitted log records for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Store a record."""
        self.records.append(record)


class VersionRoutingAndLogSchemaTests(unittest.IsolatedAsyncioTestCase):
    """Validate version-aware proxying and request log schema."""

    async def asyncSetUp(self) -> None:
        """Start upstream and gateway test servers."""
        self.upstream_requests: list[dict[str, str]] = []

        upstream_app = web.Application()
        upstream_app.router.add_route("*", "/api/{version}/{tail:.*}", self._upstream_handler)
        upstream_app.router.add_route("*", "/{rest:.*}", self._upstream_handler)
        self.upstream_server = TestServer(upstream_app)
        await self.upstream_server.start_server()
        self.upstream_client = TestClient(self.upstream_server)
        await self.upstream_client.start_server()

        settings = Settings(
            services={
                "trip-service": {
                    "url": str(self.upstream_server.make_url("/")).rstrip("/"),
                    "path_pattern": "/api/{version}/{path}",
                },
                "legacy-service": {
                    "url": str(self.upstream_server.make_url("/")).rstrip("/"),
                    "path_pattern": "/api/{path}",
                },
            },
            auth={
                "url": "http://auth-service:3000",
                "verify_endpoint": "/api/v1/verify",
            },
            service_name="api-gateway-test",
            log_level="INFO",
        )

        gateway_app = create_app(settings)
        self.gateway_server = TestServer(gateway_app)
        await self.gateway_server.start_server()
        self.gateway_client = TestClient(self.gateway_server)
        await self.gateway_client.start_server()

        self.capture_handler = _CaptureHandler()
        self.middleware_logger = logging.getLogger("src.middleware")
        self.original_middleware_level = self.middleware_logger.level
        self.middleware_logger.addHandler(self.capture_handler)
        self.middleware_logger.setLevel(logging.INFO)

        self.proxy_capture_handler = _CaptureHandler()
        self.proxy_logger = logging.getLogger("src.proxy")
        self.original_proxy_level = self.proxy_logger.level
        self.proxy_logger.addHandler(self.proxy_capture_handler)
        self.proxy_logger.setLevel(logging.WARNING)

        self.json_formatter = JsonFormatter(static_fields={"service_name": settings.service_name})

    async def asyncTearDown(self) -> None:
        """Stop test servers and restore logger state."""
        self.middleware_logger.removeHandler(self.capture_handler)
        self.middleware_logger.setLevel(self.original_middleware_level)
        self.proxy_logger.removeHandler(self.proxy_capture_handler)
        self.proxy_logger.setLevel(self.original_proxy_level)
        await self.gateway_client.close()
        await self.gateway_server.close()
        await self.upstream_client.close()
        await self.upstream_server.close()

    async def _upstream_handler(self, request: web.Request) -> web.Response:
        """Record upstream request context for assertions."""
        self.upstream_requests.append(
            {
                "path": request.path,
                "query_string": request.query_string,
                "request_id": request.headers.get("X-Request-Id", ""),
            },
        )
        return web.json_response({"ok": True})

    def _find_record(self, message: str, path: str) -> logging.LogRecord:
        """Find a captured middleware record for a concrete route path."""
        for record in reversed(self.capture_handler.records):
            if record.getMessage() == message and getattr(record, "path", None) == path:
                return record
        self.fail(f"Expected log record not found for message={message!r}, path={path!r}")

    def _format_payload(self, record: logging.LogRecord) -> dict[str, Any]:
        """Convert a log record to JSON payload using production formatter."""
        return json.loads(self.json_formatter.format(record))

    def _find_proxy_warning_record(self, message: str, path: str) -> logging.LogRecord:
        """Find a captured proxy warning record for a concrete route path."""
        for record in reversed(self.proxy_capture_handler.records):
            if (
                record.getMessage() == message
                and record.levelno == logging.WARNING
                and getattr(record, "path", None) == path
            ):
                return record
        self.fail(f"Expected proxy warning not found for message={message!r}, path={path!r}")

    async def test_v1_route_maps_and_completion_log_matches_schema(self) -> None:
        """v1 route proxies to /api/v1/... and emits required request log fields."""
        response = await self.gateway_client.get(
            "/api/v1/trip-service/orders",
            params={"limit": "10"},
            headers={"User-Agent": "gateway-test"},
        )
        self.assertEqual(response.status, 200)
        await response.json()

        self.assertEqual(len(self.upstream_requests), 1)
        upstream_request = self.upstream_requests[0]
        self.assertEqual(upstream_request["path"], "/api/v1/orders")
        self.assertEqual(upstream_request["query_string"], "limit=10")
        self.assertTrue(upstream_request["request_id"])

        record = self._find_record("request_completed", "/api/v1/trip-service/orders")
        payload = self._format_payload(record)

        self.assertTrue(_REQUEST_LOG_KEYS.issubset(payload.keys()))
        self.assertIsInstance(payload["elapsed_ms"], int)
        self.assertGreater(payload["elapsed_ms"], 0)
        self.assertEqual(payload["request_id"], upstream_request["request_id"])
        self.assertEqual(payload["status"], 200)
        self.assertEqual(payload["api_version"], "v1")

    async def test_v2_route_maps_to_v2_upstream_path(self) -> None:
        """v2 route proxies to upstream /api/v2/... path."""
        response = await self.gateway_client.get("/api/v2/trip-service/orders")
        self.assertEqual(response.status, 200)
        await response.json()

        self.assertEqual(len(self.upstream_requests), 1)
        upstream_request = self.upstream_requests[0]
        self.assertEqual(upstream_request["path"], "/api/v2/orders")
        self.assertTrue(upstream_request["request_id"])

        record = self._find_record("request_completed", "/api/v2/trip-service/orders")
        payload = self._format_payload(record)
        self.assertEqual(payload["api_version"], "v2")
        self.assertEqual(payload["status"], 200)

    async def test_non_versioned_service_rejects_versioned_route(self) -> None:
        """Versioned URL for non-versioned service returns 400 and warning."""
        response = await self.gateway_client.get("/api/v1/legacy-service/orders")
        self.assertEqual(response.status, 400)
        body = await response.json()

        self.assertEqual(body["error"], "Service does not support API versioning")
        self.assertEqual(body["service"], "legacy-service")
        self.assertEqual(self.upstream_requests, [])

        warning_record = self._find_proxy_warning_record(
            "proxy_request_rejected_service_without_version_support",
            "/api/v1/legacy-service/orders",
        )
        self.assertEqual(getattr(warning_record, "service", None), "legacy-service")
        self.assertEqual(getattr(warning_record, "api_version", None), "v1")
        self.assertEqual(getattr(warning_record, "path_pattern", None), "/api/{path}")

    async def test_non_versioned_service_proxies_via_versionless_url(self) -> None:
        """Non-versioned service is proxied when called without a version segment."""
        response = await self.gateway_client.get("/api/legacy-service/orders")
        self.assertEqual(response.status, 200)
        await response.json()

        self.assertEqual(len(self.upstream_requests), 1)
        upstream_request = self.upstream_requests[0]
        self.assertEqual(upstream_request["path"], "/api/orders")
        self.assertTrue(upstream_request["request_id"])

        record = self._find_record("request_completed", "/api/legacy-service/orders")
        payload = self._format_payload(record)
        self.assertEqual(payload["status"], 200)
        self.assertEqual(payload["service"], "legacy-service")

    async def test_invalid_version_returns_400_and_logs_error_type(self) -> None:
        """Unsupported version returns 400 and writes structured error log."""
        response = await self.gateway_client.get("/api/v3/trip-service/orders")
        self.assertEqual(response.status, 400)
        body = await response.json()
        self.assertEqual(body["error"], "Unsupported API version")
        self.assertEqual(self.upstream_requests, [])

        record = self._find_record("request_failed", "/api/v3/trip-service/orders")
        payload = self._format_payload(record)
        self.assertEqual(payload["status"], 400)
        self.assertEqual(payload["error_type"], "unsupported_api_version")
        self.assertEqual(payload["api_version"], "v3")
        self.assertEqual(payload["service"], "trip-service")


if __name__ == "__main__":
    unittest.main()
