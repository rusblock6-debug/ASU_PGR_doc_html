# ruff: noqa: D100, D101, D105

from sqlalchemy import VARCHAR, BigInteger
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from src.app.type.sync_status import SyncStatus
from src.core.database.postgres.base import Base
from src.core.database.postgres.mixin import AsDictMixin, TimestampMixin


class File(Base, TimestampMixin, AsDictMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    sync_status: Mapped[SyncStatus] = mapped_column(ENUM(SyncStatus), nullable=False)
