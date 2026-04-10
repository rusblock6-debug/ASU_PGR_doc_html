"""Reusable async parquet writer for MQTT/background consumers."""

import asyncio
import os
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Protocol, cast

import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger
from pydantic import BaseModel
from uuid_extensions import uuid7

from src.core.dto.scheme.queue import EkiperSaveFile
from src.core.parquet_writter.schema import schema_from_model

PARQUET_MAGIC = b"PAR1"


class ParquetQueueEvent(Protocol):
    """Minimal contract required by ``AsyncParquetWriter`` queue items."""

    filename: str
    row: dict[str, Any]
    topic: str
    schema: pa.Schema | None


class TaskDone(Protocol):
    """Minimal contract required by ``AsyncParquetWriter`` task Done."""

    filepath: Path


class AsyncParquetWriter[QueueItemT: ParquetQueueEvent, DoneTaskT: TaskDone]:
    """Drain an asyncio queue of events into partitioned parquet files."""

    def __init__(
        self,
        *,
        task_queue: asyncio.Queue[QueueItemT],
        done_queue: asyncio.Queue[DoneTaskT],
        destination: Path,
        batch_size: int = 200,
        flush_interval: int = 5,
        compression: str = "zstd",
        max_file_size_bytes: int = 100 * 1024 * 1024,
        create_parents: bool = True,
        done_item_factory: Callable[[Path], DoneTaskT] | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if flush_interval <= 0:
            raise ValueError("flush_interval must be positive")
        if max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be positive")

        self._task_queue = task_queue
        self._done_queue = done_queue
        self._destination = Path(destination)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._compression = compression
        self._max_file_size_bytes = max_file_size_bytes
        self._create_parents = create_parents
        self._done_factory: Callable[[Path], DoneTaskT]
        if done_item_factory is None:
            default_factory: Callable[[Path], DoneTaskT] = cast(
                Callable[[Path], DoneTaskT],
                lambda path: EkiperSaveFile(filepath=path),
            )
            self._done_factory = default_factory
        else:
            self._done_factory = done_item_factory
        if self._create_parents:
            self._destination.mkdir(parents=True, exist_ok=True)

        self._pending_events: dict[str, list[QueueItemT]] = {}
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._sinks: dict[str, _ParquetFileSink] = {}
        self._schema_cache: dict[type[BaseModel], pa.Schema] = {}
        self._topic_counters: dict[str, int] = {}

    def start(self) -> None:
        """Launch the flush loop task if it is not running."""
        if self._task and not self._task.done():
            raise RuntimeError("AsyncParquetWriter already running")
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="parquet-writer")

    async def stop(self) -> None:
        """Stop the flush loop, drain the queue, and close sinks."""
        self._stop_event.set()
        task = self._task
        if task is None:
            return
        completed_paths: list[Path] = []
        try:
            await task
        finally:
            self._task = None
            for base_filename, sink in self._sinks.items():
                try:
                    sink.close()
                    completed_paths.extend(sink.consume_finalized_parts())
                except Exception:
                    logger.exception("Failed to close parquet sink {base}", base=base_filename)
            self._sinks.clear()
        await self._notify_done(completed_paths)

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        next_flush_at = loop.time() + self._flush_interval

        while not self._stop_event.is_set():
            timeout = max(0.0, next_flush_at - loop.time())
            try:
                item = await asyncio.wait_for(self._task_queue.get(), timeout=timeout)
            except TimeoutError:
                await self._flush_if_pending()
                next_flush_at = loop.time() + self._flush_interval
                continue

            self._add_to_pending(item)
            await self._flush_if_bucket_ready(item.filename)

            if self._needs_periodic_flush(loop, next_flush_at):
                await self._flush_files()
                next_flush_at = loop.time() + self._flush_interval

        await self._drain_queue()

        await self._flush_files()

    async def _flush_if_pending(self) -> None:
        if self._pending_events:
            await self._flush_files()

    def _add_to_pending(self, item: QueueItemT) -> None:
        bucket = self._pending_events.setdefault(item.filename, [])
        bucket.append(item)
        self._task_queue.task_done()

    async def _flush_if_bucket_ready(self, filename: str) -> None:
        bucket = self._pending_events.get(filename)
        if bucket and len(bucket) >= self._batch_size:
            await self._flush_files([filename])

    def _needs_periodic_flush(self, loop: asyncio.AbstractEventLoop, next_flush_at: float) -> bool:
        return bool(self._pending_events) and loop.time() >= next_flush_at

    async def _drain_queue(self) -> None:
        while not self._task_queue.empty():
            item = await self._task_queue.get()
            self._add_to_pending(item)

    async def _flush_files(self, filenames: Iterable[str] | None = None) -> None:
        if not self._pending_events:
            return
        if filenames is None:
            selected = list(self._pending_events.keys())
        else:
            selected = [filename for filename in filenames if filename in self._pending_events]

        grouped: dict[str, list[QueueItemT]] = {}
        for filename in selected:
            events = self._pending_events.get(filename)
            if not events:
                continue
            grouped[filename] = events
            del self._pending_events[filename]

        if not grouped:
            return

        completed_paths = await asyncio.to_thread(self._write_batches, grouped)
        await self._notify_done(completed_paths)

    async def _notify_done(self, paths: list[Path]) -> None:
        if not paths:
            return

        for path in paths:
            await self._done_queue.put(self._done_factory(path))

    def _write_batches(self, grouped: dict[str, list[QueueItemT]]) -> list[Path]:
        logger.debug("writing {} file batches", len(grouped))
        completed_paths: list[Path] = []

        for base_filename, events in grouped.items():
            rows = [event.row for event in events]
            schema_hint = self._resolve_group_schema(events)

            sink = self._sinks.get(base_filename)
            if sink is None:
                sink = _ParquetFileSink(
                    base_filename=base_filename,
                    destination=self._destination,
                    compression=self._compression,
                    max_file_size_bytes=self._max_file_size_bytes,
                    schema=schema_hint,
                )
                self._sinks[base_filename] = sink

            written_rows = sink.append_rows(rows, schema=schema_hint)

            topic = getattr(events[0], "topic", base_filename) if events else base_filename
            message_count = len(events)
            row_count = written_rows
            total_messages = self._topic_counters.get(topic, 0) + message_count
            self._topic_counters[topic] = total_messages
            current_path = sink.current_path
            completed_paths.extend(sink.consume_finalized_parts())
            logger.debug(
                (
                    "Topic {topic} accepted {message_count} messages (total {total_messages}); "
                    "wrote {row_count} rows to {path} (file total {file_rows})"
                ),
                topic=topic,
                message_count=message_count,
                total_messages=total_messages,
                row_count=row_count,
                path=str(current_path) if current_path else base_filename,
                file_rows=sink.total_rows_written,
            )

        return completed_paths

    def _resolve_group_schema(self, events: list[QueueItemT]) -> pa.Schema | None:
        for event in events:
            schema = self._resolve_event_schema(event)
            if schema is not None:
                return schema
        return None

    @staticmethod
    def _align_to_schema(table: pa.Table, schema: pa.Schema) -> pa.Table:
        cols = []
        for field in schema:
            if field.name in table.column_names:
                col = table[field.name]
                if not col.type.equals(field.type):
                    col = col.cast(field.type, safe=False)
                cols.append(col)
            else:
                cols.append(pa.nulls(table.num_rows, type=field.type))
        return pa.Table.from_arrays(cols, schema=schema)

    def _resolve_event_schema(self, event: QueueItemT) -> pa.Schema | None:
        schema = getattr(event, "schema", None)
        if schema is not None:
            return schema

        model: type[BaseModel] | None = getattr(event, "schema_model", None)
        if model is None or not isinstance(model, type) or not issubclass(model, BaseModel):
            return None

        cached = self._schema_cache.get(model)
        if cached is None:
            cached = schema_from_model(model)
            self._schema_cache[model] = cached
        return cached


class _ParquetFileSink:
    """Append-only writer with deterministic rotation logic."""

    def __init__(
        self,
        *,
        base_filename: str,
        destination: Path,
        compression: str,
        max_file_size_bytes: int,
        schema: pa.Schema | None = None,
    ) -> None:
        self._base_filename = base_filename
        self._destination = destination
        self._compression = compression
        self._max_file_size_bytes = max_file_size_bytes
        self._preferred_schema = schema

        path_info = Path(base_filename)
        self._stem = path_info.stem or base_filename
        self._suffix = path_info.suffix or ""

        self._current_part: str | None = None
        self._current_path: Path | None = None
        self._current_temp_path: Path | None = None
        self._current_size = 0
        self._schema: pa.Schema | None = None
        self._writer: pq.ParquetWriter | None = None
        self._finalized_parts: list[Path] = []
        self._written_rows = 0
        self._recover_incomplete_parts()
        self._start_new_part()

    def append_rows(self, rows: list[dict[str, Any]], schema: pa.Schema | None = None) -> int:
        if not rows:
            return 0

        desired_schema = schema or self._preferred_schema
        table = pa.Table.from_pylist(rows, schema=desired_schema)
        table = self._prepare_table(table, desired_schema)
        writer = self._writer
        temp_path = self._current_temp_path
        if writer is None or temp_path is None:
            msg = "Parquet writer is not initialized"
            raise RuntimeError(msg)
        writer.write_table(table)
        self._current_size = temp_path.stat().st_size
        row_count = table.num_rows
        self._written_rows += row_count
        return row_count

    def close(self) -> None:
        self._close_writer(finalize=True)

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    @property
    def total_rows_written(self) -> int:
        return self._written_rows

    def consume_finalized_parts(self) -> list[Path]:
        if not self._finalized_parts:
            return []
        finalized = self._finalized_parts
        self._finalized_parts = []
        return finalized

    def _prepare_table(self, table: pa.Table, desired_schema: pa.Schema | None) -> pa.Table:
        if self._writer is None:
            self._schema = desired_schema or table.schema
            if desired_schema and not table.schema.equals(desired_schema):
                table = AsyncParquetWriter._align_to_schema(table, desired_schema)
            self._open_writer()
            return table

        if self._should_rotate_by_size(table):
            self._roll_part()
            return self._prepare_table(table, desired_schema)

        if self._schema is None:
            msg = "Parquet schema must be resolved before writing"
            raise RuntimeError(msg)

        if desired_schema and not desired_schema.equals(self._schema):
            logger.debug(
                "Rotating {} because schema changed",
                self._base_filename,
            )
            self._roll_part()
            return self._prepare_table(table, desired_schema)

        extra_cols = [name for name in table.column_names if name not in self._schema.names]
        if extra_cols:
            logger.debug(
                "Rotating {} because of new columns {}",
                self._base_filename,
                extra_cols,
            )
            self._roll_part()
            return self._prepare_table(table, desired_schema)

        if table.schema != self._schema:
            table = AsyncParquetWriter._align_to_schema(table, self._schema)

        return table

    def _should_rotate_by_size(self, table: pa.Table) -> bool:
        if self._current_size >= self._max_file_size_bytes:
            return True
        estimated_add = table.nbytes or 0
        return (self._current_size + estimated_add) >= self._max_file_size_bytes

    def _open_writer(self) -> None:
        if self._schema is None or self._current_temp_path is None:
            msg = "Cannot open parquet writer without schema and temp path"
            raise RuntimeError(msg)
        self._writer = pq.ParquetWriter(
            where=str(self._current_temp_path),
            schema=self._schema,
            compression=self._compression,
            use_dictionary=True,
        )

    def _roll_part(self) -> None:
        self._close_writer()
        self._start_new_part()
        logger.debug(
            "Rolling {} to part {}",
            self._base_filename,
            self._current_part,
        )

    def _close_writer(self, *, finalize: bool = False) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        if self._current_temp_path and self._current_temp_path.exists():
            if self._current_path is None:
                msg = "Cannot finalize parquet part without destination path"
                raise RuntimeError(msg)
            self._current_temp_path.replace(self._current_path)
            self._current_size = self._current_path.stat().st_size
            self._finalized_parts.append(self._current_path)

    def _generate_part_id(self) -> str:
        return uuid7(as_type="hex")

    def _part_name(self, part_id: str) -> str:
        return f"{self._stem}.part{part_id}{self._suffix}"

    def _temp_name(self, part_id: str) -> str:
        return f"{self._part_name(part_id)}.tmp"

    def _start_new_part(self) -> None:
        self._current_part = self._generate_part_id()
        self._current_path = self._destination / self._part_name(self._current_part)
        self._current_temp_path = self._destination / self._temp_name(self._current_part)
        if self._current_temp_path.exists():
            self._current_temp_path.unlink()
        self._current_size = 0
        self._schema = None
        self._writer = None
        self._written_rows = 0

    def _recover_incomplete_parts(self) -> None:
        pattern = self._temp_part_glob_pattern()
        for temp_path in sorted(self._destination.glob(pattern)):
            self._finalize_orphaned_temp_file(temp_path)

    def _temp_part_glob_pattern(self) -> str:
        suffix = self._suffix or ""
        return f"{self._stem}.part*{suffix}.tmp"

    def _finalize_orphaned_temp_file(self, temp_path: Path) -> None:
        if not temp_path.is_file():
            return
        final_path = temp_path.with_suffix("")
        if self._is_valid_parquet_file(temp_path):
            self._move_temp_to_final(temp_path, final_path)
            return
        if self._seal_truncated_parquet(temp_path):
            logger.warning("Sealed truncated parquet temp file {}", temp_path)
            self._move_temp_to_final(temp_path, final_path)
            return
        logger.warning("Discarding incomplete parquet temp file {}", temp_path)
        temp_path.unlink(missing_ok=True)

    @classmethod
    def _move_temp_to_final(cls, temp_path: Path, final_path: Path) -> None:
        try:
            temp_path.replace(final_path)
        except OSError:
            logger.warning("Failed to finalize temp parquet {}", temp_path)

    @classmethod
    def _is_valid_parquet_file(cls, path: Path) -> bool:
        try:
            size = path.stat().st_size
            magic_size = len(PARQUET_MAGIC)
            if size < magic_size * 2:
                return False
            with path.open("rb") as file:
                if file.read(magic_size) != PARQUET_MAGIC:
                    return False
                file.seek(-magic_size, os.SEEK_END)
                return file.read(magic_size) == PARQUET_MAGIC
        except OSError:
            return False

    @classmethod
    def _seal_truncated_parquet(cls, path: Path) -> bool:
        try:
            with path.open("r+b") as file:
                if file.read(len(PARQUET_MAGIC)) != PARQUET_MAGIC:
                    return False
                file.seek(0, os.SEEK_END)
                file.write(PARQUET_MAGIC)
            try:
                pq.read_metadata(path)
            except Exception:
                return False
            return True
        except OSError:
            return False
