import base64
import time

import jwt
import pytest
from fastapi import HTTPException

from auth_lib.token import decode_token
from auth_lib.schemas import UserPayload
from tests.conftest import make_token, SAMPLE_PAYLOAD


def test_decode_valid_token():
    token = make_token()
    user = decode_token(token)
    assert user.username == "testuser"
    assert user.id == 1


def test_decode_returns_user_payload_type():
    token = make_token()
    user = decode_token(token)
    assert isinstance(user, UserPayload)


def test_decode_expired_token_raises_401():
    token = make_token(exp=int(time.time()) - 100)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_decode_malformed_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-jwt")
    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail


def test_decode_invalid_payload_raises_401():
    token = jwt.encode({"foo": "bar"}, "s", algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401
    assert "payload" in exc_info.value.detail.lower()


def test_decode_preserves_permission_names():
    token = make_token()
    user = decode_token(token)
    names = [p.name for p in user.role.permissions]
    assert "work-time-map" in names


def test_decode_corrupted_jwt_body_raises_401():
    """JWT with valid header but non-JSON base64 payload -> 401."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(b"not-json").rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    malformed = f"{header}.{payload}.{sig}"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(malformed)
    assert exc_info.value.status_code == 401


def test_decode_missing_permissions_field_raises_401():
    """JWT payload with role missing 'permissions' key -> 401."""
    token = jwt.encode(
        {
            "id": 1,
            "username": "x",
            "role": {"id": 1, "name": "r"},
            "exp": int(time.time()) + 3600,
        },
        "a-secret-key-that-is-long-enough!",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401
