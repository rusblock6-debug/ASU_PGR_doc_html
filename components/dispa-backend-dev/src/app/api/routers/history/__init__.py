from fastapi import APIRouter

from . import history, place

router = APIRouter(
    tags=["history"],
)
router.include_router(history.router)
router.include_router(place.router)

__all__ = ["router"]
