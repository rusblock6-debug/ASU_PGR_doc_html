from fastapi import APIRouter
from . import auth, users, roles, permission, staff

router = APIRouter(
    prefix="/v1",
)

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(permission.router)
router.include_router(staff.router)


__all__ = ["router"]