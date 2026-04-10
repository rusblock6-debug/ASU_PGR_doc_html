import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import model, repository
from tests.fake.repository.trip_repository import FakeTripRepository


@pytest.fixture(scope="function")
def fake_trip_repository(async_session) -> FakeTripRepository:
    trip_id = uuid.uuid4()
    return FakeTripRepository(
        async_session,
        cycle_state_history=[
            {"id": 1, "state": "A", "trip_id": str(trip_id)},
            {"id": 2, "state": "B", "trip_id": str(trip_id)},
        ],
        cycle_tag_history=[
            {"id": 10, "tag": "X", "trip_id": str(trip_id)},
            {"id": 11, "tag": "X", "trip_id": str(trip_id)},
        ],
        cycles=[
            {"id": 100, "trip_id": str(trip_id)},
        ],
    )


@pytest_asyncio.fixture(loop_scope="function")
async def file_repository(async_session: AsyncSession) -> repository.FileRepository:
    return repository.FileRepository(model=model.File, db_session=async_session)


@pytest_asyncio.fixture(loop_scope="function")
async def trip_service_dump_repository(
    async_session: AsyncSession,
) -> repository.TripServiceDumpRepository:
    return repository.TripServiceDumpRepository(
        model=model.TripServiceDump,
        db_session=async_session,
    )
