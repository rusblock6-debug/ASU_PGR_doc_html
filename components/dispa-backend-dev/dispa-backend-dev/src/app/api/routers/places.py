"""API endpoints для работы с местами (places)."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.services.place_info import get_place

place_router = APIRouter(prefix="/places", tags=["places"])


@place_router.get("/{place_id}")
async def get_place_endpoint(place_id: int) -> Any:
    """Получить Place по ID из graph-service."""
    place_data = await get_place(place_id)

    if place_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Место с ID {place_id} не найдено",
        )

    return place_data
