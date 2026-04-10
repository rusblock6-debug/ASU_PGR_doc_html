"""Integration tests for FastAPI dependency chain (require_permission, get_current_user)."""

import time

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth_lib import Permission, Action, UserPayload, require_permission, get_current_user
from tests.conftest import make_token, SAMPLE_PAYLOAD


@pytest.fixture()
def app() -> FastAPI:
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(
        user: UserPayload | None = Depends(require_permission(Permission.WORK_ORDER, Action.VIEW)),
    ):
        if user is None:
            return {"user_id": None}
        return {"user_id": user.id, "username": user.username}

    @test_app.get("/edit-protected")
    async def edit_protected(
        user: UserPayload | None = Depends(require_permission(Permission.WORK_ORDER, Action.EDIT)),
    ):
        if user is None:
            return {"user_id": None}
        return {"user_id": user.id, "username": user.username}

    @test_app.get("/staff-only")
    async def staff_only(
        user: UserPayload | None = Depends(require_permission(Permission.STAFF, Action.VIEW)),
    ):
        if user is None:
            return {"user_id": None}
        return {"user_id": user.id, "username": user.username}

    @test_app.get("/timemap")
    async def timemap(
        user: UserPayload | None = Depends(require_permission(Permission.WORK_TIME_MAP, Action.VIEW)),
    ):
        if user is None:
            return {"user_id": None}
        return {"user_id": user.id}

    @test_app.get("/me")
    async def me(user: UserPayload | None = Depends(get_current_user)):
        if user is None:
            return {"user_id": None}
        return {"user_id": user.id, "username": user.username}

    return test_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Source": "api-gateway"}


class TestRequirePermission:
    """Tests for require_permission dependency factory."""

    def test_allows_valid_token(self, client: TestClient):
        """GET /protected with valid token containing work_order can_view=True -> 200."""
        token = make_token()
        resp = client.get("/protected", headers=_auth_header(token))
        assert resp.status_code == 200

    def test_returns_user_payload(self, client: TestClient):
        """Response body has user_id and username matching token payload."""
        token = make_token()
        resp = client.get("/protected", headers=_auth_header(token))
        data = resp.json()
        assert data["user_id"] == SAMPLE_PAYLOAD["id"]
        assert data["username"] == SAMPLE_PAYLOAD["username"]

    def test_denies_missing_action(self, client: TestClient):
        """GET /edit-protected with token where work_order can_edit=False -> 403."""
        payload = dict(SAMPLE_PAYLOAD)
        payload["role"] = {
            "id": 1,
            "name": "viewer",
            "permissions": [
                {"id": 1, "name": "work_order", "can_view": True, "can_edit": False},
            ],
        }
        token = make_token(payload)
        resp = client.get("/edit-protected", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_denies_missing_permission(self, client: TestClient):
        """GET /staff-only with token that has no staff permission -> 403."""
        # SAMPLE_PAYLOAD has work_order and work-time-map, but NOT staff
        token = make_token()
        resp = client.get("/staff-only", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_missing_token_returns_401(self, client: TestClient):
        """GET /protected with X-Source: api-gateway but no Authorization header -> 401."""
        resp = client.get("/protected", headers={"X-Source": "api-gateway"})
        assert resp.status_code == 401

    def test_malformed_token_returns_401(self, client: TestClient):
        """GET /protected with 'Bearer not-a-jwt' -> 401."""
        resp = client.get("/protected", headers={"Authorization": "Bearer not-a-jwt", "X-Source": "api-gateway"})
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client: TestClient):
        """GET /protected with expired token -> 401."""
        token = make_token(exp=int(time.time()) - 100)
        resp = client.get("/protected", headers=_auth_header(token))
        assert resp.status_code == 401

    def test_empty_permissions_returns_403(self, client: TestClient):
        """GET /protected with empty permissions array -> 403."""
        payload = dict(SAMPLE_PAYLOAD)
        payload["role"] = {
            "id": 1,
            "name": "empty",
            "permissions": [],
        }
        token = make_token(payload)
        resp = client.get("/protected", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_hyphen_permission_works_through_chain(self, client: TestClient):
        """GET /timemap with work-time-map permission -> 200."""
        token = make_token()
        resp = client.get("/timemap", headers=_auth_header(token))
        assert resp.status_code == 200


class TestRequirePermissionInternalBypass:
    """Tests for require_permission internal request bypass via X-Source header."""

    def test_no_x_source_header_returns_none(self, client: TestClient):
        """GET /protected without X-Source header -> returns None (internal request)."""
        resp = client.get("/protected")
        assert resp.status_code == 200
        assert resp.json()["user_id"] is None

    def test_x_source_not_api_gateway_returns_none(self, client: TestClient):
        """GET /protected with X-Source != api-gateway -> returns None (internal request)."""
        resp = client.get("/protected", headers={"X-Source": "internal-service"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] is None

    def test_x_source_api_gateway_with_valid_token(self, client: TestClient):
        """GET /protected with X-Source: api-gateway and valid token -> full permission check."""
        token = make_token()
        headers = {**_auth_header(token), "X-Source": "api-gateway"}
        resp = client.get("/protected", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["user_id"] == SAMPLE_PAYLOAD["id"]

    def test_x_source_api_gateway_without_token_returns_401(self, client: TestClient):
        """GET /protected with X-Source: api-gateway but no token -> 401."""
        resp = client.get("/protected", headers={"X-Source": "api-gateway"})
        assert resp.status_code == 401

    def test_x_source_api_gateway_missing_permission_returns_403(self, client: TestClient):
        """GET /staff-only with X-Source: api-gateway but no staff permission -> 403."""
        token = make_token()
        headers = {**_auth_header(token), "X-Source": "api-gateway"}
        resp = client.get("/staff-only", headers=headers)
        assert resp.status_code == 403


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    def test_returns_payload(self, client: TestClient):
        """GET /me with valid token and X-Source: api-gateway -> 200 with user data."""
        token = make_token()
        headers = {**_auth_header(token), "X-Source": "api-gateway"}
        resp = client.get("/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == SAMPLE_PAYLOAD["id"]
        assert data["username"] == SAMPLE_PAYLOAD["username"]

    def test_no_token_returns_401(self, client: TestClient):
        """GET /me with X-Source: api-gateway but no token -> 401."""
        resp = client.get("/me", headers={"X-Source": "api-gateway"})
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client: TestClient):
        """GET /me with X-Source: api-gateway and expired token -> 401."""
        token = make_token(exp=int(time.time()) - 100)
        headers = {**_auth_header(token), "X-Source": "api-gateway"}
        resp = client.get("/me", headers=headers)
        assert resp.status_code == 401

    def test_malformed_token_returns_401(self, client: TestClient):
        """GET /me with X-Source: api-gateway and malformed token -> 401."""
        resp = client.get("/me", headers={"Authorization": "Bearer not-a-jwt", "X-Source": "api-gateway"})
        assert resp.status_code == 401

    def test_no_x_source_header_returns_none(self, client: TestClient):
        """GET /me without X-Source header -> returns None (internal request)."""
        resp = client.get("/me")
        assert resp.status_code == 200
        assert resp.json()["user_id"] is None

    def test_x_source_not_api_gateway_returns_none(self, client: TestClient):
        """GET /me with X-Source != api-gateway -> returns None (internal request)."""
        resp = client.get("/me", headers={"X-Source": "internal-service"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] is None

    def test_x_source_api_gateway_requires_token(self, client: TestClient):
        """GET /me with X-Source: api-gateway requires valid token (normal auth flow)."""
        token = make_token()
        headers = {**_auth_header(token), "X-Source": "api-gateway"}
        resp = client.get("/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["user_id"] == SAMPLE_PAYLOAD["id"]


class TestClosureCapture:
    """Verify require_permission closures capture different permissions correctly."""

    def test_different_permissions_work_independently(self, client: TestClient):
        """GET /protected and GET /staff-only use different permission checks."""
        token = make_token()
        # work_order is in SAMPLE_PAYLOAD -> /protected should pass
        resp_protected = client.get("/protected", headers=_auth_header(token))
        assert resp_protected.status_code == 200
        # staff is NOT in SAMPLE_PAYLOAD -> /staff-only should fail
        resp_staff = client.get("/staff-only", headers=_auth_header(token))
        assert resp_staff.status_code == 403
