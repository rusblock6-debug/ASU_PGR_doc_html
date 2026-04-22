"""Enums для ShiftTask."""

from enum import StrEnum


class ShiftTaskStatusEnum(StrEnum):
    """Статусы выполнения ShiftTask."""

    PENDING = "PENDING"  # Ожидает выполнения
    IN_PROGRESS = "IN_PROGRESS"  # В процессе выполнения
    COMPLETED = "COMPLETED"  # Завершено
    CANCELLED = "CANCELLED"  # Отменено
