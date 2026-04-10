"""SSE endpoints, сгруппированные в Swagger под тегом Events."""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.vehicles import VehicleStateEventList
from app.services.route_progress_stream import routes_progress_stream
from app.services.vehicle_stream import vehicle_state_stream

events_stream_router = APIRouter(prefix="/events", tags=["Events"])


@events_stream_router.get("/stream/routes")
async def stream_routes_progress(request: Request) -> StreamingResponse:
    """SSE: прогресс техники на активных маршрутах (см. trip-service /api/fleet-control)."""
    return StreamingResponse(
        routes_progress_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@events_stream_router.get(
    "/stream/vehicles",
    response_model=VehicleStateEventList,
    responses={
        200: {
            "description": "SSE-поток изменений состояния ТС (text/event-stream). "
            "Каждое `data:` сообщение — JSON-массив объектов VehicleStateEvent.",
        },
    },
)
async def stream_vehicle_state(request: Request) -> StreamingResponse:
    """SSE: статус ТС, горизонт и последнее место по тегу."""
    return StreamingResponse(
        vehicle_state_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
