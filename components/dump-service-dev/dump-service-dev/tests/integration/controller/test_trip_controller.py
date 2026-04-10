import tarfile
import uuid
from pathlib import Path

import pytest

from src.app import controller
from src.app.controller import trip_controller as trip_controller_module
from src.app.type import SyncStatus
from src.core.config import get_settings
from src.core.exception import InternalServerException

settings = get_settings()


@pytest.fixture
def dump_generation_env(monkeypatch, tmp_path) -> list[Path]:
    monkeypatch.setattr(settings, "DUMP_STORAGE_DIR", tmp_path)

    temp_files: list[Path] = []

    def fake_named_tempfile(*_, **kwargs):
        suffix = kwargs.get("suffix", "")
        temp_path = tmp_path / f"dataset_{len(temp_files)}{suffix}"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.touch()
        temp_files.append(temp_path)

        class _FakeTempFile:
            def __init__(self, name: str) -> None:
                self.name = name

            def close(self) -> None:
                return None

        return _FakeTempFile(str(temp_path))

    monkeypatch.setattr(
        trip_controller_module.tempfile,
        "NamedTemporaryFile",
        fake_named_tempfile,
    )

    return temp_files


async def test_generate_trip_dump(
    tmp_path,
    trip_id,
    trip_controller: controller.TripController,
    dump_generation_env,
):
    temp_files = dump_generation_env

    dump = await trip_controller.generate_dump(trip_id)

    expected_archive = tmp_path / "trip-service" / f"{settings.TRUCK_ID}_{trip_id}.tar.gz"
    assert dump.files[0].path == str(expected_archive)
    assert dump.trip_id == trip_id
    assert dump.files[0].sync_status == SyncStatus.CREATED
    assert expected_archive.exists()

    with tarfile.open(expected_archive, mode="r:gz") as archive:
        archive_members = {member.name for member in archive.getmembers()}

    expected_members = {
        f"{trip_id}/cycle_state_history.parquet",
        f"{trip_id}/cycle_tag_history.parquet",
        f"{trip_id}/cycles.parquet",
        f"{trip_id}/cycles.parquet",
        f"{trip_id}/trips.parquet",
        f"{trip_id}/cycle_analytics.parquet",
    }
    assert archive_members == expected_members
    assert all(not temp_path.exists() for temp_path in temp_files)


async def test_generate_trip_dump_disk_full(
    monkeypatch,
    trip_id,
    trip_controller: controller.TripController,
    dump_generation_env,
):
    temp_files = dump_generation_env
    disk_full_trip_id = f"{trip_id}-{uuid.uuid4()}"

    def raise_no_space(*_args, **_kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(
        controller.TripController,
        "_flush_batch",
        staticmethod(raise_no_space),
    )

    with pytest.raises(InternalServerException) as exc:
        await trip_controller.generate_dump(disk_full_trip_id)

    assert exc.value.detail == "Failed to write dump archive"
    assert all(not temp_path.exists() for temp_path in temp_files)


async def test_generate_trip_dump_parquet(
    tmp_path,
    trip_controller: controller.TripController,
    dump_generation_env,
):
    trip_id = uuid.uuid4().hex
    dump = await trip_controller.generate_dump_parquet(trip_id)

    expected_dir = tmp_path / "trip_service" / f"{trip_id}_{settings.TRUCK_ID}"
    expected_files = {
        "cycle_state_history.parquet",
        "cycle_tag_history.parquet",
        "cycles.parquet",
        "trips.parquet",
        "cycle_analytics.parquet",
    }
    expected_paths = {str(expected_dir / name) for name in expected_files}
    dump_paths = {file.path for file in dump.files}
    assert dump_paths == expected_paths
    assert dump.trip_id == trip_id
    assert all(file.sync_status == SyncStatus.CREATED for file in dump.files)
    assert expected_dir.exists()
    assert expected_dir.is_dir()

    actual_files = {path.name for path in expected_dir.iterdir() if path.is_file()}
    assert actual_files == expected_files


async def test_generate_trip_dump_parquet_disk_full(
    monkeypatch,
    trip_controller: controller.TripController,
    dump_generation_env,
):
    trip_id = uuid.uuid4().hex

    def raise_no_space(*_args, **_kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(trip_controller, "_write_rows_to_parquet", raise_no_space)

    with pytest.raises(InternalServerException) as exc:
        await trip_controller.generate_dump_parquet(trip_id)

    assert exc.value.detail == "Failed to write parquet file"
