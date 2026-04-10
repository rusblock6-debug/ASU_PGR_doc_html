"""Кастомные исключения для Trip Service."""

from typing import Any


class TripServiceError(Exception):
    """Базовое исключение Trip Service."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class StateMachineError(TripServiceError):
    """Ошибки State Machine."""

    pass


class TripManagementError(TripServiceError):
    """Ошибки управления рейсами."""

    pass


class TaskManagementError(TripServiceError):
    """Ошибки управления заданиями."""

    pass


class RedisConnectionError(TripServiceError):
    """Ошибки подключения к Redis."""

    pass


class MQTTConnectionError(TripServiceError):
    """Ошибки подключения к MQTT."""

    pass


class DatabaseError(TripServiceError):
    """Ошибки базы данных."""

    pass
