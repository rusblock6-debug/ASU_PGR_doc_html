"""Tests for audit_lib.fastapi -- AuditMiddleware and _decode_jwt_sub."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from audit_lib.context import audit_user_var, get_audit_user
from audit_lib.fastapi import AuditMiddleware, _decode_jwt_sub

BASE_URL = "http://test"


def _make_jwt(payload: dict[str, Any]) -> str:
    """Create an unsigned JWT with the given payload for testing."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.sig"


def _bearer(payload: dict[str, Any]) -> dict[str, str]:
    """Return an Authorization header dict with a Bearer JWT."""
    return {"Authorization": f"Bearer {_make_jwt(payload)}"}


# -------------------------------------------------------------------
# _decode_jwt_sub
# -------------------------------------------------------------------


class TestDecodeJwtSub:
    """Unit tests for the _decode_jwt_sub helper function."""

    def test_valid_jwt_returns_sub(self) -> None:
        """Valid JWT with sub claim returns the sub value."""
        token = _make_jwt({"sub": "user-42"})
        assert _decode_jwt_sub(token) == "user-42"

    def test_not_a_jwt_returns_none(self) -> None:
        """Non-JWT string returns None."""
        assert _decode_jwt_sub("not-a-jwt") is None

    def test_non_json_payload_returns_none(self) -> None:
        """JWT with non-JSON payload returns None."""
        assert _decode_jwt_sub("a.bm90LWpzb24.c") is None

    def test_empty_payload_returns_none(self) -> None:
        """JWT with empty JSON object returns None."""
        assert _decode_jwt_sub("a.e30.c") is None

    def test_payload_needing_padding(self) -> None:
        """JWT payload requiring base64 padding decodes OK."""
        result = _decode_jwt_sub("a.eyJzdWIiOiAidXNlci00MiJ9.c")
        assert result == "user-42"

    def test_integer_sub_returned_as_string(self) -> None:
        """Numeric sub claim is coerced to string."""
        token = _make_jwt({"sub": 123})
        assert _decode_jwt_sub(token) == "123"

    def test_empty_string_returns_none(self) -> None:
        """Empty string input returns None."""
        assert _decode_jwt_sub("") is None


# -------------------------------------------------------------------
# _extract_user_id
# -------------------------------------------------------------------


class TestExtractUserId:
    """Isolated unit tests for AuditMiddleware._extract_user_id."""

    def test_valid_bearer_extracts_sub(self) -> None:
        """Valid Bearer header with JWT containing sub claim returns the sub value."""
        mw = AuditMiddleware(None)  # type: ignore[arg-type]
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", f"Bearer {_make_jwt({'sub': 'u1'})}".encode()),
            ],
        }
        assert mw._extract_user_id(scope) == "u1"

    def test_no_auth_header_returns_none(self) -> None:
        """No authorization header returns None."""
        mw = AuditMiddleware(None)  # type: ignore[arg-type]
        scope = {"type": "http", "headers": []}
        assert mw._extract_user_id(scope) is None

    def test_malformed_jwt_returns_none(self) -> None:
        """Malformed JWT in Bearer header returns None."""
        mw = AuditMiddleware(None)  # type: ignore[arg-type]
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer not-a-jwt")],
        }
        assert mw._extract_user_id(scope) is None

    def test_wrong_scheme_returns_none(self) -> None:
        """Wrong auth scheme (Basic) returns None."""
        mw = AuditMiddleware(None)  # type: ignore[arg-type]
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Basic dXNlcjpwYXNz")],
        }
        assert mw._extract_user_id(scope) is None


# -------------------------------------------------------------------
# AuditMiddleware
# -------------------------------------------------------------------


def _build_app() -> FastAPI:
    """Create a minimal FastAPI app with AuditMiddleware."""
    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.get("/whoami")
    async def whoami() -> dict[str, str | None]:
        """Return the current audit user."""
        return {"user": get_audit_user()}

    @app.get("/error")
    async def error_route() -> None:
        """Raise an error to test contextvar cleanup."""
        raise RuntimeError("boom")

    return app


def _transport(
    app: FastAPI,
    *,
    raise_app_exceptions: bool = True,
) -> httpx.ASGITransport:
    """Build an ASGITransport for the given app."""
    return httpx.ASGITransport(  # type: ignore[arg-type]
        app=app,
        raise_app_exceptions=raise_app_exceptions,
    )


class TestAuditMiddleware:
    """Integration tests for AuditMiddleware via httpx."""

    @pytest.mark.asyncio
    async def test_valid_bearer_sets_user(self) -> None:
        """Valid Bearer token sets audit_user_var."""
        app = _build_app()
        async with httpx.AsyncClient(
            transport=_transport(app), base_url=BASE_URL
        ) as client:
            resp = await client.get("/whoami", headers=_bearer({"sub": "user-42"}))
        assert resp.status_code == 200
        assert resp.json() == {"user": "user-42"}

    @pytest.mark.asyncio
    async def test_no_auth_header_leaves_none(self) -> None:
        """No Authorization header leaves audit_user_var None."""
        app = _build_app()
        async with httpx.AsyncClient(
            transport=_transport(app), base_url=BASE_URL
        ) as client:
            resp = await client.get("/whoami")
        assert resp.status_code == 200
        assert resp.json() == {"user": None}

    @pytest.mark.asyncio
    async def test_contextvar_reset_after_request(self) -> None:
        """audit_user_var resets to None after request."""
        app = _build_app()
        async with httpx.AsyncClient(
            transport=_transport(app), base_url=BASE_URL
        ) as client:
            await client.get("/whoami", headers=_bearer({"sub": "user-42"}))
        assert audit_user_var.get() is None

    @pytest.mark.asyncio
    async def test_contextvar_reset_on_exception(self) -> None:
        """audit_user_var resets even on inner app exception."""
        app = _build_app()
        t = _transport(app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=t, base_url=BASE_URL) as client:
            resp = await client.get("/error", headers=_bearer({"sub": "user-42"}))
        assert resp.status_code == 500
        assert audit_user_var.get() is None

    @pytest.mark.asyncio
    async def test_malformed_jwt_passes_through(self) -> None:
        """Malformed JWT passes through, user stays None."""
        app = _build_app()
        async with httpx.AsyncClient(
            transport=_transport(app), base_url=BASE_URL
        ) as client:
            resp = await client.get(
                "/whoami",
                headers={"Authorization": "Bearer not-a-jwt"},
            )
        assert resp.status_code == 200
        assert resp.json() == {"user": None}

    @pytest.mark.asyncio
    async def test_wrong_auth_scheme_passes_through(self) -> None:
        """Non-Bearer auth scheme passes through."""
        app = _build_app()
        async with httpx.AsyncClient(
            transport=_transport(app), base_url=BASE_URL
        ) as client:
            resp = await client.get(
                "/whoami",
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
            )
        assert resp.status_code == 200
        assert resp.json() == {"user": None}

    @pytest.mark.asyncio
    async def test_lifespan_passthrough(self) -> None:
        """Non-HTTP scopes pass through untouched."""
        called = False

        async def fake_app(
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            nonlocal called
            called = True

        mw = AuditMiddleware(fake_app)  # type: ignore[arg-type]
        await mw({"type": "lifespan"}, None, None)  # type: ignore[arg-type]
        assert called
