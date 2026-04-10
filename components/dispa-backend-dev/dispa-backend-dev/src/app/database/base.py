"""SQLAlchemy Base и общие утилиты для моделей."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""

    pass


class TimestampMixin:
    """Миксин для автоматического добавления created_at и updated_at."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Миксин для UUID первичного ключа."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


def generate_uuid() -> str:
    """Генерация ID для trip."""
    return str(uuid.uuid4())


def generate_uuid_vehicle_id(vehicle_id: int) -> str:
    """Генерация UUID для записей с vehicle_id для снижения коллизий."""
    return f"{str(uuid.uuid4())}_{vehicle_id}"
