"""API endpoints для истории."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.schemas.history.history import HistoryEventType, HistoryItem
from app.factory import Factory
from app.services.history_service import HistoryService

router = APIRouter(
    prefix="/history",
)


@router.get("")
async def get_history(
    vehicle_id: int = Query(),
    from_datetime: datetime = Query(),
    to_datetime: datetime = Query(),
    event_type: list[HistoryEventType] | None = Query(None),
    history_service: HistoryService = Depends(Factory.get_history_service),
) -> list[HistoryItem]:
    """Получить историю."""
    result = await history_service.get_history(
        vehicle_id=vehicle_id,
        from_datetime=from_datetime,
        to_datetime=to_datetime,
        event_types=event_type,
    )
    return result
