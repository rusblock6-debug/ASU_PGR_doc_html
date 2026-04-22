"""Конкретная реализация AggregateHandler: применяет FanOutPayload в PostgreSQL."""

from __future__ import annotations

import time
from typing import Any

import asyncpg
import msgspec
from loguru import logger

from src.app.factories.service_factory import ServiceFactory
from src.app.model.fan_out_payload import FanOutPayloadMsg, TableBatch
from src.app.outbox import OutboxWriter
from src.core.aggregate_handler import FanOutPayload
from src.core.aggregator import AggregatedBatch

# DDL для таблицы seq_id — создаётся один раз при старте consumer
_CDC_SEQ_ID_DDL = """
CREATE TABLE IF NOT EXISTS cdc_seq_id (
    queue TEXT PRIMARY KEY,
    last_seq_id BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_SEQ_ID_UPSERT = """
INSERT INTO cdc_seq_id (queue, last_seq_id, updated_at)
VALUES ($1, $2, now())
ON CONFLICT (queue) DO UPDATE
    SET last_seq_id = EXCLUDED.last_seq_id,
        updated_at = now()
"""

_SEQ_ID_SELECT = "SELECT last_seq_id FROM cdc_seq_id WHERE queue = $1"


class AggregateApplier:
    """
    Применяет FanOutPayload агрегат в PostgreSQL в одной транзакции.

    Реализует AggregateHandler Protocol (handle + handle_raw).
    Используется AmqpConsumer: consumer вызывает handle_raw(body),
    AggregateApplier декодирует, проверяет дубликат, применяет, сохраняет seq_id.
    Если что-то идёт не так — исключение всплывает наверх, consumer делает nack.
    """

    def __init__(
        self,
        factory: ServiceFactory,
        service_name: str,
        queue_name: str,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        """
        Args:
            factory: ServiceFactory для получения DB pool и applier'ов
            service_name: Имя сервиса ("graph", "enterprise", "auth", "trip")
            queue_name: Имя очереди — используется как ключ в cdc_seq_id
            outbox_writer: Опциональный writer для записи уведомлений в outbox
        """
        self._factory = factory
        self._service_name = service_name
        self._queue_name = queue_name
        self._outbox_writer = outbox_writer
        self._decoder = msgspec.json.Decoder(FanOutPayloadMsg)

    async def setup(self) -> None:
        """Создать cdc_seq_id таблицу если не существует. Вызвать до start()."""
        async with self._factory.pool.acquire() as conn:
            await conn.execute(_CDC_SEQ_ID_DDL)
        logger.info(
            "cdc_seq_id table ready service={service}",
            service=self._service_name,
        )

    async def handle_raw(self, body: bytes) -> None:
        """Точка входа из AmqpConsumer. Декодирует и вызывает handle."""
        msg = self._decoder.decode(body)
        await self._apply(msg)

    async def handle(self, payload: FanOutPayload) -> None:
        """Применить FanOutPayload в PostgreSQL."""
        # payload здесь — FanOutPayloadMsg (удовлетворяет FanOutPayload Protocol)
        assert isinstance(payload, FanOutPayloadMsg)
        await self._apply(payload)

    async def _apply(self, payload: FanOutPayloadMsg) -> None:
        """Основная логика применения: dedup check + транзакция."""
        tables: dict[str, TableBatch] = payload.tables
        upsert_count = sum(len(b.upserts) for b in tables.values())
        delete_count = sum(len(b.deletes) for b in tables.values())
        logger.info(
            "Message received service={service} seq_id={seq_id} tables={tables}"
            " upserts={upserts} deletes={deletes}",
            service=self._service_name,
            seq_id=payload.seq_id,
            tables=len(tables),
            upserts=upsert_count,
            deletes=delete_count,
        )

        # Dedup check — отдельное соединение, вне транзакции данных
        async with self._factory.pool.acquire() as conn:
            row = await conn.fetchrow(_SEQ_ID_SELECT, self._queue_name)
        if row is not None and payload.seq_id <= row["last_seq_id"]:
            logger.warning(
                "Duplicate seq_id detected — skipping service={service}"
                " seq_id={seq_id} last_known={last}",
                service=self._service_name,
                seq_id=payload.seq_id,
                last=row["last_seq_id"],
            )
            return

        start = time.monotonic()

        async with self._factory.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET CONSTRAINTS ALL DEFERRED")
                for table_name, table_batch in tables.items():
                    applier = self._factory.get_or_create_applier(table_name)
                    batch: AggregatedBatch[dict[str, Any]] = AggregatedBatch(
                        upserts=table_batch.upserts,
                        deletes=table_batch.deletes,
                    )
                    await applier.apply_in_transaction(conn, batch)
                # Outbox — пишем уведомления внутри той же транзакции
                if self._outbox_writer is not None:
                    await self._outbox_writer.process(conn, payload)
                # Hook для подклассов — выполняется внутри транзакции
                await self._post_apply_hook(conn, payload)

                # seq_id сохраняется в той же транзакции — атомарно с данными
                await conn.execute(_SEQ_ID_UPSERT, self._queue_name, payload.seq_id)

        elapsed = time.monotonic() - start
        logger.info(
            "Apply complete service={service} seq_id={seq_id} elapsed={elapsed:.3f}s",
            service=self._service_name,
            seq_id=payload.seq_id,
            elapsed=elapsed,
        )

    async def _post_apply_hook(
        self,
        conn: asyncpg.Connection[Any],
        payload: FanOutPayloadMsg,
    ) -> None:
        """Hook для подклассов: вызывается внутри транзакции после apply всех таблиц."""
