"""SQLAlchemy модели для хранения offset'ов стримов."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db.base import Base


class BortStreamOffset(Base):
    """Таблица для хранения offset'ов стримов по бортам."""

    __tablename__ = "bort_stream_offsets"

    stream_name: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    bort_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    offset_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seq_id: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
