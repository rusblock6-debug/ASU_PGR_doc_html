"""WebSocket менеджер соединений и вспомогательные функции для FastAPI"""

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Глобальная ссылка на event loop для отправки из других потоков
_event_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    """Установить event loop для использования в broadcast из других потоков"""
    global _event_loop
    _event_loop = loop


def get_event_loop() -> asyncio.AbstractEventLoop | None:
    """Получить event loop"""
    return _event_loop


class ConnectionManager:
    """Менеджер WebSocket соединений"""

    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str = "default"):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)
        logger.info(f"Client connected to room: {room}")

    def disconnect(self, websocket: WebSocket, room: str = "default"):
        if room in self.active_connections:
            self.active_connections[room].discard(websocket)
            logger.info(f"Client disconnected from room: {room}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_room(self, room: str, message: dict):
        if room in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[room]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            # Удаляем отключенные соединения
            for conn in disconnected:
                self.active_connections[room].discard(conn)

    async def broadcast(self, message: dict):
        for room in self.active_connections:
            await self.broadcast_to_room(room, message)


# Глобальный менеджер соединений
manager = ConnectionManager()


def broadcast_to_room_sync(room: str, message: dict):
    """Синхронная функция для отправки сообщения в комнату.
    Используется из MQTT callback (другой поток).
    """
    loop = get_event_loop()
    if loop is None:
        logger.warning("Event loop not set, cannot broadcast message")
        return

    try:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast_to_room(room, message),
            loop,
        )
    except Exception as e:
        logger.error(f"Error in broadcast_to_room_sync: {e}")
