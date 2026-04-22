"""Перечисления для маршрутных заданий."""

from enum import StrEnum


class TripStatusRouteEnum(StrEnum):
    """Статусы маршрутного задания."""

    ACTIVE = "ACTIVE"  # В работе
    REJECTED = "REJECTED"  # Отклонено
    SENT = "SENT"  # Отправлено
    DELIVERED = "DELIVERED"  # Доставлено
    COMPLETED = "COMPLETED"  # Завершено
    EMPTY = "EMPTY"  # К заполнению
    PAUSED = "PAUSED"  # На паузе


class TypesRouteTaskEnum(StrEnum):
    """Типы маршрутных заданий."""

    LOADING_SHAS = "LOADING_SHAS"  # Погрузка в ШАС
    LOADING_TRANSPORT_GM = "LOADING_TRANSPORT_GM"  # Погрузка/транспортировка ГМ
    HOUSEKEEPING_TRIPS = "HOUSEKEEPING_TRIPS"  # Хоз. Рейсы
