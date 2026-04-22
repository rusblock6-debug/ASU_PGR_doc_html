from fastapi import APIRouter

from . import cycle_tag_history

router = APIRouter(
    prefix="/trip_service",
    tags=["Trip Service"],
)

router.include_router(cycle_tag_history.router)

__all__ = ["router"]
