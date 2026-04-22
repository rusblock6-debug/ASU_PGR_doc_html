import time

import jwt


SAMPLE_PAYLOAD = {
    "id": 1,
    "username": "testuser",
    "role": {
        "id": 1,
        "name": "admin",
        "permissions": [
            {"id": 1, "name": "work_order", "can_view": True, "can_edit": True},
            {"id": 2, "name": "work-time-map", "can_view": True, "can_edit": False},
        ],
    },
    "exp": int(time.time()) + 3600,
}


def make_token(payload: dict | None = None, **overrides) -> str:
    """Generate a JWT string for testing.

    Uses SAMPLE_PAYLOAD by default. Supports overrides for any top-level key.
    """
    data = dict(payload or SAMPLE_PAYLOAD)
    data.update(overrides)
    return jwt.encode(data, "secret", algorithm="HS256")
