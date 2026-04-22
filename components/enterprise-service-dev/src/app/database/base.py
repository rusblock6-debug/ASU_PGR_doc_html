"""Base классы для моделей SQLAlchemy."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""

    pass


class TimestampMixin:
    """Миксин для добавления временных меток."""

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Время создания записи."""
        return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Время обновления записи."""
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
