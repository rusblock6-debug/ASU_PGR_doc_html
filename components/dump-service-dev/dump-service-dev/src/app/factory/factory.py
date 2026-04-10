# ruff: noqa: D102
"""Фабрика."""

from functools import partial
from typing import TYPE_CHECKING, cast

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

from src.app.model import File, TripServiceDump
from src.app.repository import FileRepository, TripRepository, TripServiceDumpRepository
from src.core.config import get_settings
from src.core.database import db_session, trip_db_session
from src.core.database.postgres.dependency import PostgresSession

if TYPE_CHECKING:
    from src.app.controller import FileController, TripController


settings = get_settings()


class Factory:
    """Фабрика.

    Это контейнер фабрики, который будет создавать все контроллеры и репозитории,
    к которым сможет получить доступ остальная часть приложения.
    """

    # repositories
    file_repository = staticmethod(
        partial(FileRepository, model=File),
    )
    trip_service_dump_repository = staticmethod(
        partial(TripServiceDumpRepository, model=TripServiceDump),
    )
    trip_repository = TripRepository

    def get_trip_controller(
        self,
        session: AsyncSession | async_scoped_session[AsyncSession] = Depends(
            PostgresSession(db_session=db_session),
        ),
        trip_session: AsyncSession | async_scoped_session[AsyncSession] = Depends(
            PostgresSession(db_session=trip_db_session),
        ),
    ) -> "TripController":
        from src.app.controller import TripController

        writer_session = cast(AsyncSession, session)
        trip_reader_session = cast(AsyncSession, trip_session)
        return TripController(
            trip_service_dump_repository=self.trip_service_dump_repository(
                db_session=writer_session,
            ),
            trip_repository=self.trip_repository(db_session=trip_reader_session),
            exclude_fields=settings.EXCLUDE_FIELDS,
        )

    def get_file_controller(
        self,
        session: AsyncSession | async_scoped_session[AsyncSession] = Depends(
            PostgresSession(db_session=db_session),
        ),
    ) -> "FileController":
        from src.app.controller import FileController

        writer_session = cast(AsyncSession, session)
        return FileController(
            file_repository=self.file_repository(db_session=writer_session),
            exclude_fields=settings.EXCLUDE_FIELDS,
        )
