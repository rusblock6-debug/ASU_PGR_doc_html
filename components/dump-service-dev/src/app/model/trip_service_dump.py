# ruff: noqa: D100, D101, D105
from typing import TYPE_CHECKING

from sqlalchemy import VARCHAR, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.postgres.base import Base
from src.core.database.postgres.mixin import AsDictMixin

if TYPE_CHECKING:
    from src.app.model import File


class TripServiceDumpFile(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dump_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trip_service_dump.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("file.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("dump_id", "file_id", name="uq_dump_file"),)


class TripServiceDump(Base, AsDictMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(
        VARCHAR(255),
        unique=True,
        nullable=False,
    )  # TODO: как починят в трип сервисе заменить на uuid

    files: Mapped[list["File"]] = relationship(
        "File",
        lazy="selectin",
        cascade="save-update",
        secondary=TripServiceDumpFile.__table__,
    )
