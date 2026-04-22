# ruff: noqa: D100, D101
# mypy: disable-error-code="type-arg"
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.model import TripServiceDump
from src.core.repository import SQLAlchemyRepository


class TripServiceDumpRepository(SQLAlchemyRepository[TripServiceDump, AsyncSession, Select]):
    pass
