# ruff: noqa: D100, D101
# mypy: disable-error-code="type-arg,arg-type,union-attr,misc"
import tarfile
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger
from sqlalchemy.engine import RowMapping

from src.app.exception import DumpIsAlreadyGenerated
from src.app.model import File, TripServiceDump
from src.app.repository import (
    TripRepository,
    TripServiceDumpRepository,
)
from src.app.type import SyncStatus
from src.core.config import get_settings
from src.core.controller import SQLAlchemyController
from src.core.exception import (
    InternalServerException,
    NotFoundException,
)

settings = get_settings()
PARQUET_BATCH_SIZE = 1_000


class TripController(SQLAlchemyController[TripServiceDump]):
    def __init__(
        self,
        trip_service_dump_repository: TripServiceDumpRepository,
        trip_repository: TripRepository,
        exclude_fields: list[str],
    ):
        super().__init__(
            model=TripServiceDump,
            repository=trip_service_dump_repository,
            exclude_fields=exclude_fields,
        )
        self.trip_service_dump_repository = trip_service_dump_repository
        self.trip_repository = trip_repository
        self._parquet_batch_size = PARQUET_BATCH_SIZE

    def _get_dump_files(self, trip_id: str) -> dict[str, AsyncIterator[RowMapping]]:
        files: dict[str, AsyncIterator[RowMapping]] = {
            "cycle_state_history.parquet": self.trip_repository.get_cycle_state_history(trip_id),
            "cycle_tag_history.parquet": self.trip_repository.get_cycle_tag_history(trip_id),
            "cycles.parquet": self.trip_repository.get_cycle(trip_id),
            "trips.parquet": self.trip_repository.get_trip(trip_id),
            "cycle_analytics.parquet": self.trip_repository.get_cycle_analytics(trip_id),
        }

        return files

    async def generate_dump(self, trip_id: str) -> TripServiceDump:
        """Генерация архива для рейса.

        Со следующими файлами:
            1. cycle_state_history
            2. cycle_tag_history
            ...

        :param trip_id: id рейса
        :return: File
        """
        # Проверка есть ли уже сгенерированный архив по рейсу
        try:
            await self.get_by(
                field="trip_id",
                value=trip_id,
                unique=True,
            )

            raise DumpIsAlreadyGenerated()

        # Если записи нет игнорируем ошибку
        except NotFoundException:
            pass

        archive_path = (
            settings.DUMP_STORAGE_DIR / "trip-service" / f"{settings.TRUCK_ID}_{trip_id}.tar.gz"
        )
        context = {"trip_id": trip_id, "archive": str(archive_path)}
        logger.info("Trip dump generation started", **context)

        try:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.bind(**context).exception("Failed to prepare destination directory")
            raise InternalServerException("Failed to prepare dump directory") from exc

        try:
            archive_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.bind(**context).exception("Failed to clean existing archive")
            raise InternalServerException("Failed to prepare dump archive") from exc

        files = self._get_dump_files(trip_id)

        try:
            with tarfile.open(archive_path, mode="w:gz") as archive:
                for filename, generator in files.items():
                    await self._write_dataset_to_archive(
                        rows=generator,
                        dataset_name=filename,
                        archive=archive,
                        arc_prefix=trip_id,
                    )
        except OSError as exc:
            logger.bind(**context).exception("Failed to write dump archive")
            raise InternalServerException("Failed to write dump archive") from exc

        logger.info("Trip dump archive created", **context)

        result = await self.create_model(
            TripServiceDump(
                files=[
                    File(
                        path=str(archive_path),
                        sync_status=SyncStatus.CREATED,
                    ),
                ],
                trip_id=trip_id,
            ),
        )

        return result

    async def generate_dump_parquet(self, trip_id: str) -> TripServiceDump:
        """Генерация parquet-файлов для рейса без архива.

        Со следующими файлами:
            1. cycle_state_history
            2. cycle_tag_history
            ...

        :param trip_id: id рейса
        :return: File
        """
        dump_dir = settings.DUMP_STORAGE_DIR / "trip_service" / f"{trip_id}_{settings.TRUCK_ID}"
        context = {"trip_id": trip_id, "dump_dir": str(dump_dir)}
        logger.info("Trip parquet dump generation started", **context)

        try:
            dump_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.bind(**context).exception("Failed to prepare destination directory")
            raise InternalServerException("Failed to prepare dump directory") from exc

        files = self._get_dump_files(trip_id)

        required_filenames = set(files.keys())

        existing_dump = await self.repository.get_by(
            field="trip_id",
            value=trip_id,
            unique=True,
        )
        if existing_dump is None:
            saved_filenames: set[str] = set()
        else:
            saved_filenames = {Path(file.path).name for file in existing_dump.files}

        new_files: list[File] = []
        for filename in required_filenames - saved_filenames:
            generator = files[filename]
            file_path = dump_dir / filename

            try:
                await self._write_rows_to_parquet(
                    rows=generator,
                    destination=file_path,
                    dataset_name=filename,
                )
            except OSError as exc:
                logger.bind(**context).exception(
                    "Failed to write parquet file",
                    file=str(file_path),
                )
                raise InternalServerException("Failed to write parquet file") from exc
            new_files.append(
                File(
                    path=str(file_path),
                    sync_status=SyncStatus.CREATED,
                ),
            )

        logger.info("Trip parquet dump created", **context)

        if existing_dump is None:
            return await self.create_model(
                TripServiceDump(
                    files=new_files,
                    trip_id=trip_id,
                ),
            )

        if new_files:
            existing_dump.files.extend(new_files)
            await self.repository.session.flush()

        return existing_dump

    async def _write_rows_to_parquet(
        self,
        rows: AsyncIterator[RowMapping],
        destination: Path,
        dataset_name: str,
    ) -> None:
        context = {
            "dataset": dataset_name,
            "file": str(destination),
        }
        writer: pq.ParquetWriter | None = None
        batch: list[dict[str, Any]] = []
        rows_written = 0

        async for row in rows:
            batch.append(dict(row))
            rows_written += 1
            if len(batch) >= self._parquet_batch_size:
                # блокирует loop
                writer = self._flush_batch(batch, destination, writer)
                batch.clear()

        if batch:
            # блокирует loop
            writer = self._flush_batch(batch, destination, writer)

        if writer is None and not destination.exists():
            destination.touch(exist_ok=True)
        logger.info("Parquet rows written", rows=rows_written, **context)

        if writer is not None:
            writer.close()

    async def _write_dataset_to_archive(
        self,
        rows: AsyncIterator[RowMapping],
        dataset_name: str,
        archive: tarfile.TarFile,
        arc_prefix: str,
    ) -> None:
        context = {
            "dataset": dataset_name,
            "archive": archive.name,
        }
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        except OSError as exc:
            logger.bind(**context).exception("Failed to prepare temporary parquet file")
            raise InternalServerException("Failed to prepare temporary parquet file") from exc

        temp_path = Path(temp_file.name)
        temp_file.close()
        try:
            await self._write_rows_to_parquet(
                rows=rows,
                destination=temp_path,
                dataset_name=dataset_name,
            )
            arcname = f"{arc_prefix}/{dataset_name}" if arc_prefix else dataset_name
            try:
                archive.add(temp_path, arcname=arcname)
            except OSError as exc:
                logger.bind(**context).exception(
                    "Failed to add dataset to archive",
                    arcname=arcname,
                )
                raise InternalServerException("Failed to add dataset to archive") from exc
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def _flush_batch(
        batch: list[dict[str, Any]],
        destination: Path,
        writer: pq.ParquetWriter | None,
    ) -> pq.ParquetWriter:
        table = pa.Table.from_pylist(batch)
        if writer is None:
            writer = pq.ParquetWriter(destination, table.schema)
        writer.write_table(table)
        return writer
