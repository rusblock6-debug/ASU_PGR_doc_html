"""WebSocket обработчики для отслеживания транспорта"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket_client import manager
from app.services.ws_vehicle_tracking import vehicle_tracking_ws_service

logger = logging.getLogger(__name__)

websocket_router = APIRouter(prefix="/ws", tags=["WebSocket"])


@websocket_router.websocket("/vehicle-tracking")
async def vehicle_tracking_websocket(websocket: WebSocket):
    """WebSocket для отслеживания транспортных средств"""
    await manager.connect(websocket, "vehicle_tracking")
    try:
        while True:
            data = await websocket.receive_json()

            action = data.get("action")

            if action == "get_current_location":
                vehicle_id = data.get("vehicle_id", "4_truck")
                try:
                    location_data = await vehicle_tracking_ws_service.get_current_location(
                        vehicle_id,
                    )
                    if location_data:
                        await manager.send_personal_message(
                            {"type": "current_location", "data": location_data},
                            websocket,
                        )
                    else:
                        await manager.send_personal_message(
                            {"type": "current_location", "error": "No location data found"},
                            websocket,
                        )
                except Exception as e:
                    logger.error(f"Error getting current location: {e}")
                    await manager.send_personal_message(
                        {"type": "error", "message": "Failed to get current location"},
                        websocket,
                    )

            elif action == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "vehicle_tracking")
        logger.info("Client disconnected from vehicle tracking WebSocket")
