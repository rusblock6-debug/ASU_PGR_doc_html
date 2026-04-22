"""API endpoints для истории остатков."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.history import PlaceRemainingHistoryCreate, PlaceRemainingHistoryResponse
from app.services.place_remaining import place_remaining_service
from app.utils.session import SessionDepends

router = APIRouter(
    prefix="/history",
)


@router.post("/place", response_model=PlaceRemainingHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_place_history(
    body: PlaceRemainingHistoryCreate,
    session: SessionDepends,
) -> Any:
    """Создать запись истории изменения остатков.

    Используется graph-service для сохранения истории при ручном изменении.
    Нормализация target_stock, согласование change_volume/change_weight и плотности — в
    `PlaceRemainingService.create_history`.
    """
    try:
        return await place_remaining_service.create_history(session, body, notify_graph=False)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
