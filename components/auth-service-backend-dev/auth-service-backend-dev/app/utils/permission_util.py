from app.models.user_model import User

async def has_permission(user: User, permission_name: str) -> bool:
    for perm in user.role.permissions:
        if perm.name == permission_name or perm.name == "admin":
            return True
    return False
