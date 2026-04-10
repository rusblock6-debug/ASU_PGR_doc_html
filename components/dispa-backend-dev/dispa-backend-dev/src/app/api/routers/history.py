"""API endpoints для истории остатков."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.history import PlaceRemainingHistoryCreate, PlaceRemainingHistoryResponse
from app.enums import RemainingChangeTypeEnum
from app.services.place_info import get_place_stock
from app.services.place_remaining import place_remaining_service
from app.utils.session import SessionDepends

router = APIRouter()


@router.post("/place-history", response_model=PlaceRemainingHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_place_history(
    body: PlaceRemainingHistoryCreate,
    session: SessionDepends,
) -> Any:
    """Создать запись истории изменения остатков.

    Используется graph-service для сохранения истории при ручном изменении.
    """
    # Для ручных изменений веса/остатка места удобно передавать целевое значение (target_stock).
    # Тогда мы создаём корректирующую запись (delta), чтобы сумма истории стала равна target_stock.
    if body.change_type == RemainingChangeTypeEnum.manual and body.target_stock is not None:
        current_stock = await get_place_stock(place_id=body.place_id, db=session)
        body.change_amount = round(float(body.target_stock) - float(current_stock), 1)

    if body.change_amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="change_amount is required (or provide target_stock for manual correction)",
        )

    return await place_remaining_service.create_history(session, body, notify_graph=False)
