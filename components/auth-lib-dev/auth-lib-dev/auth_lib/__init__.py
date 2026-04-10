"""auth_lib -- FastAPI JWT authentication and permission checking library."""

from auth_lib.permissions import Permission, Action
from auth_lib.schemas import UserPayload, RoleSchema, PermissionSchema
from auth_lib.dependencies import require_permission, get_current_user

__all__ = [
    "Permission",
    "Action",
    "UserPayload",
    "RoleSchema",
    "PermissionSchema",
    "require_permission",
    "get_current_user",
]
