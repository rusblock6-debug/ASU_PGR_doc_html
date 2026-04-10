import pytest_asyncio

from src.app import controller, repository
from src.core.config import get_settings
from tests.fake import repository as fake_repository

settings = get_settings()


@pytest_asyncio.fixture(loop_scope="function")
async def trip_controller(
    fake_trip_repository: fake_repository.FakeTripRepository,
    trip_service_dump_repository: repository.TripServiceDumpRepository,
) -> controller.TripController:
    return controller.TripController(
        trip_service_dump_repository=trip_service_dump_repository,
        trip_repository=fake_trip_repository,
        exclude_fields=settings.EXCLUDE_FIELDS,
    )
