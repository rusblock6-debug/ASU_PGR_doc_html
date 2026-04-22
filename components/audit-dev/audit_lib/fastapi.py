"""ASGI middleware that extracts JWT identity and sets the audit contextvar."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

try:
    from starlette.types import ASGIApp, Receive, Scope, Send
except ImportError as exc:
    raise ImportError(
        "starlette is required for AuditMiddleware. "
        "Install it with: pip install audit-lib[fastapi]"
    ) from exc

from audit_lib.context import audit_user_var

logger = logging.getLogger("audit_lib.fastapi")


def _decode_jwt_sub(token: str, claim: str = "sub") -> str | None:
    """Decode a JWT payload and return the value of *claim*, or ``None``.

    Only the payload (second dot-separated segment) is decoded.
    No signature verification is performed — this is intentional because
    the upstream gateway already validates tokens.

    Parameters
    ----------
    token:
        The raw JWT string (``header.payload.signature``).
    claim:
        The claim name to extract (default ``"sub"``).

    Returns
    -------
    str | None
        The claim value coerced to ``str``, or ``None`` if extraction fails.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:  # noqa: PLR2004
            return None
        payload_b64 = parts[1]
        # Add padding — base64 requires length to be a multiple of 4
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload: dict[str, Any] = json.loads(payload_bytes)
        value = payload.get(claim)
        if value is None:
            return None
        return str(value)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        logger.debug("Failed to decode JWT payload", exc_info=True)
        return None


class AuditMiddleware:
    """Pure ASGI middleware that sets ``audit_user_var`` from a JWT Bearer token.

    The middleware extracts the ``sub`` claim (configurable via *user_claim*)
    from the ``Authorization: Bearer <token>`` header and sets the
    ``audit_user_var`` contextvar for the duration of the request.

    Only HTTP scopes are processed — WebSocket and lifespan scopes pass
    through untouched.

    Parameters
    ----------
    app:
        The next ASGI application in the stack.
    user_claim:
        JWT claim to use as the user identifier (default ``"sub"``).

    Examples
    --------
    ::

        from fastapi import FastAPI
        from audit_lib.fastapi import AuditMiddleware

        app = FastAPI()
        app.add_middleware(AuditMiddleware)
    """

    def __init__(self, app: ASGIApp, *, user_claim: str = "sub") -> None:
        self.app = app
        self.user_claim = user_claim

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an ASGI event."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        user_id = self._extract_user_id(scope)
        if user_id is None:
            await self.app(scope, receive, send)
            return

        token = audit_user_var.set(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            audit_user_var.reset(token)

    def _extract_user_id(self, scope: Scope) -> str | None:
        """Extract user identity from the Authorization header."""
        headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        for name, value in headers:
            if name == b"authorization":
                auth_value = value.decode("latin-1")
                if auth_value.lower().startswith("bearer "):
                    raw_token = auth_value[7:]
                    return _decode_jwt_sub(raw_token, claim=self.user_claim)
                return None
        return None
