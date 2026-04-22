import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.model import File, TripServiceDump
from src.app.model.trip_service_dump import TripServiceDumpFile
from src.app.type import SyncStatus


def _make_file(path_suffix: str) -> File:
    return File(
        path=f"/tmp/dump-{path_suffix}.parquet",
        sync_status=SyncStatus.CREATED,
    )


async def test_trip_service_dump_link_table_inserts(async_session: AsyncSession) -> None:
    file_one = _make_file(uuid.uuid4().hex)
    file_two = _make_file(uuid.uuid4().hex)
    dump = TripServiceDump(
        trip_id=uuid.uuid4().hex,
        files=[file_one, file_two],
    )

    async_session.add(dump)
    await async_session.commit()

    rows = (
        await async_session.execute(
            select(TripServiceDumpFile).where(TripServiceDumpFile.dump_id == dump.id)
        )
    ).scalars().all()
    assert len(rows) == 2
    assert {row.dump_id for row in rows} == {dump.id}
    assert {row.file_id for row in rows} == {file_one.id, file_two.id}

    persisted_dump = await async_session.get(TripServiceDump, dump.id)
    assert {file.id for file in persisted_dump.files} == {file_one.id, file_two.id}


async def test_trip_service_dump_link_table_unique(async_session: AsyncSession) -> None:
    file_one = _make_file(uuid.uuid4().hex)
    dump = TripServiceDump(trip_id=uuid.uuid4().hex, files=[file_one])

    async_session.add(dump)
    await async_session.commit()

    duplicate_link = TripServiceDumpFile(dump_id=dump.id, file_id=file_one.id)
    async_session.add(duplicate_link)

    with pytest.raises(IntegrityError):
        await async_session.commit()

    await async_session.rollback()


async def test_trip_service_dump_link_table_cascade_on_dump_delete(
    async_session: AsyncSession,
) -> None:
    file_one = _make_file(uuid.uuid4().hex)
    file_two = _make_file(uuid.uuid4().hex)
    dump = TripServiceDump(
        trip_id=uuid.uuid4().hex,
        files=[file_one, file_two],
    )

    async_session.add(dump)
    await async_session.commit()

    await async_session.delete(dump)
    await async_session.commit()

    rows = (
        await async_session.execute(
            select(TripServiceDumpFile).where(TripServiceDumpFile.dump_id == dump.id)
        )
    ).scalars().all()
    assert rows == []

    remaining_files = (
        await async_session.execute(
            select(File.id).where(File.id.in_([file_one.id, file_two.id]))
        )
    ).scalars().all()
    assert set(remaining_files) == {file_one.id, file_two.id}
