"""Репозиторий, который ходит в базу Trip Service сырыми SQL без моделей."""

# ruff: noqa: D102
from collections.abc import AsyncIterator

from loguru import logger
from sqlalchemy import RowMapping, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception import (
    InternalServerException,
)


class TripRepository:
    """Репозиторий для получения данных из Trip Service."""

    def __init__(
        self,
        db_session: AsyncSession,
    ) -> None:
        self.db_session = db_session

    async def get_cycle_state_history(self, trip_id: str) -> AsyncIterator[RowMapping]:
        """История стейтов по рейсу.

        :param trip_id: id рейса
        :return: AsyncIterator[RowMapping]
        """
        query = """
        select * from "cycle_state_history" where "cycle_id" = :trip_id
        order by timestamp
        """
        context = {"trip_id": trip_id, "dataset": "cycle_state_history"}
        try:
            result = await self.db_session.stream(text(query), {"trip_id": trip_id})
        except SQLAlchemyError as exc:
            logger.bind(**context).exception("Failed to execute cycle state history query")
            raise InternalServerException("Failed to fetch cycle state history") from exc

        try:
            async for row in result.mappings():
                yield row
        except SQLAlchemyError as exc:
            logger.bind(**context).exception("Failed to iterate cycle state history result")
            raise InternalServerException("Unable to stream cycle state history") from exc

    async def get_cycle_tag_history(self, trip_id: str) -> AsyncIterator[RowMapping]:
        """История тегов по рейсу.

        :param trip_id: id рейса
        :return: AsyncIterator[RowMapping]
        """
        query = """
        select * from "cycle_tag_history" where cycle_id = :trip_id
        order by timestamp
        """
        context = {"trip_id": trip_id, "dataset": "cycle_tag_history"}
        try:
            result = await self.db_session.stream(text(query), {"trip_id": trip_id})
        except SQLAlchemyError as exc:
            logger.bind(**context).exception("Failed to execute cycle tag history query")
            raise InternalServerException("Failed to fetch cycle tag history") from exc

        try:
            async for row in result.mappings():
                yield row
        except SQLAlchemyError as exc:
            logger.bind(**context).exception("Failed to iterate cycle tag history result")
            raise InternalServerException("Unable to stream cycle tag history") from exc

    async def get_cycle(self, trip_id: str) -> AsyncIterator[RowMapping]:
        """Цикл по рейсу.

        :param trip_id: id рейса
        :return: Row
        """
        query = """
        select * from "cycles" where cycle_id = :trip_id
        limit 1
        """
        context = {"trip_id": trip_id, "dataset": "cycle"}
        try:
            result = await self.db_session.execute(text(query), {"trip_id": trip_id})
        except SQLAlchemyError as exc:
            logger.bind(**context).exception("Failed to execute cycle tag history query")
            raise InternalServerException("Failed to fetch cycle tag history") from exc

        row = result.mappings().first()
        if row:
            yield row

    async def get_trip(self, trip_id: str) -> AsyncIterator[RowMapping]:
        """рейс по trip_id.

        :param trip_id: id рейса
        :return: Row
        """
        query = """
        select * from "trips" where cycle_id = :trip_id
        limit 1
        """
        context = {"trip_id": trip_id, "dataset": "trip"}
        try:
            result = await self.db_session.execute(text(query), {"trip_id": trip_id})
        except SQLAlchemyError as exc:
            logger.bind(**context).exception("Failed to execute cycle tag history query")
            raise InternalServerException("Failed to fetch cycle tag history") from exc
        else:
            row = result.mappings().first()
            if row:
                yield row

    async def get_cycle_analytics(self, trip_id: str) -> AsyncIterator[RowMapping]:
        """аналитика по trip_id.

        :param trip_id: id рейса
        :return: Row
        """
        query = """
        select * from "cycle_analytics" where cycle_id = :trip_id
        limit 1
        """
        context = {"trip_id": trip_id, "dataset": "cycle_analytics"}
        try:
            result = await self.db_session.execute(text(query), {"trip_id": trip_id})
        except SQLAlchemyError as exc:
            logger.bind(**context).exception("Failed to execute cycle tag history query")
            raise InternalServerException("Failed to fetch cycle tag history") from exc
        else:
            row = result.mappings().first()
            if row:
                yield row
