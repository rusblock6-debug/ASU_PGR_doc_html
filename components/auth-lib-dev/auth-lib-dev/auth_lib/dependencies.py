"""FastAPI dependency factories for JWT authentication and permission checking."""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth_lib.permissions import Permission, Action
from auth_lib.schemas import UserPayload
from auth_lib.token import decode_token

security = HTTPBearer(auto_error=False)


def _has_permission(user: UserPayload, permission: Permission, action: Action) -> bool:
    """Check if user has a specific permission/action pair."""
    for perm in user.role.permissions:
        if perm.name == permission.value:
            if action == Action.VIEW and perm.can_view:
                return True
            if action == Action.EDIT and perm.can_edit:
                return True
            break
    return False


def require_permission(*pairs: tuple[Permission, Action]):
    """Factory returning a FastAPI dependency that allows access if ANY permission matches.

    Usage:
        Depends(require_any_permission(
            (Permission.TRIP_EDITOR, Action.VIEW),
            (Permission.WORK_ORDER, Action.VIEW),
        ))

    Returns UserPayload on success, None for internal (non-gateway) requests.
    Raises 401 without token, 403 if no permission matches.
    """
    async def dependency(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> UserPayload | None:
        if request.headers.get("X-Source") != "api-gateway":
            return None
        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing bearer token")
        user = decode_token(credentials.credentials)

        has_permissions = (_has_permission(user, permission, action) for permission, action in pairs)

        if any(has_permissions):
            return user
        permission_list = ", ".join(f"{p.value} ({a.value})" for p, a in pairs)
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: requires any of [{permission_list}]",
        )

    return dependency


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserPayload | None:
    """FastAPI dependency that decodes JWT and returns UserPayload without permission check.

    If X-Source header is missing or not equal to 'api-gateway', returns None
    to allow internal service-to-service calls without authentication.

    Usage: Depends(get_current_user)
    """
    if request.headers.get("X-Source") != "api-gateway":
        return None
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return decode_token(credentials.credentials)
