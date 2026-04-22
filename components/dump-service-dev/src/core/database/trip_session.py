# ruff: noqa: D100, D101, D102
# mypy: disable-error-code="type-arg"


from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings
from src.core.database.postgres.session import RoutingSession, get_session_context

settings = get_settings()
engines = {
    "reader": create_async_engine(
        str(settings.TRIP_SERVICE_SETTINGS.POSTGRES_URL),
        pool_recycle=1800,
        pool_pre_ping=True,
    ),
    "writer": create_async_engine(
        str(settings.TRIP_SERVICE_SETTINGS.POSTGRES_URL),
        pool_recycle=1800,
        pool_pre_ping=True,
    ),
}


async_session_factory = async_sessionmaker(
    class_=AsyncSession,
    sync_session_class=RoutingSession,
    expire_on_commit=False,
    engines=engines,
)

trip_db_session: AsyncSession | async_scoped_session = async_scoped_session(
    session_factory=async_session_factory,
    scopefunc=get_session_context,
)
