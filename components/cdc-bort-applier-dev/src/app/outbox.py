"""Outbox-паттерн: декларативные правила уведомлений и writer."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any

import asyncpg
import msgspec
from loguru import logger

from src.app.model.fan_out_payload import FanOutPayloadMsg

_OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS outbox (
    id         bigserial      PRIMARY KEY,
    queue_name text           NOT NULL,
    payload    jsonb          NOT NULL,
    created_at timestamptz    NOT NULL DEFAULT now(),
    sent_at    timestamptz
)
"""

_OUTBOX_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS ix_outbox_unsent
    ON outbox (created_at)
    WHERE sent_at IS NULL
"""

_OUTBOX_INSERT = """
INSERT INTO outbox (queue_name, payload)
VALUES ($1, $2::jsonb)
"""


class CdcOp(StrEnum):
    """Debezium CDC operation codes."""

    CREATE = "c"
    UPDATE = "u"
    DELETE = "d"
    READ = "r"


class MessageEvent(StrEnum):
    create = "create"
    update = "update"
    delete = "delete"
    read = "read"

    @classmethod
    def op_mapper(cls, op: CdcOp) -> MessageEvent:
        match op:
            case CdcOp.CREATE:
                return cls.create
            case CdcOp.UPDATE:
                return cls.update
            case CdcOp.DELETE:
                return cls.delete
            case CdcOp.READ:
                return cls.read
            case _:
                raise ValueError(f"Unsupported CDC operation: {op}")


class MessageData(msgspec.Struct, frozen=True):
    """Базовый набор полей сообщения."""

    message_type: str
    message_id: uuid.UUID = msgspec.field(default_factory=uuid.uuid4)
    message_event: MessageEvent = MessageEvent.create
    message_timestamp: datetime = msgspec.field(
        default_factory=lambda: datetime.now(UTC),
    )


class OutboxNotification(msgspec.Struct, frozen=True):
    """Базовый класс уведомлений."""

    payload: dict[str, Any]
    message_data: MessageData


@dataclass(frozen=True, slots=True)
class OutboxRule:
    """Декларативное правило: какая таблица → запись в outbox."""

    table: str
    queue_name: str
    ops: frozenset[CdcOp]


class OutboxWriter:
    """Переиспользуемый writer: по правилам проверяет payload и пишет в outbox."""

    def __init__(self, rules: Sequence[OutboxRule]) -> None:
        self._rules = rules
        self._encoder = msgspec.json.Encoder()

    async def setup(self, pool: asyncpg.Pool[Any]) -> None:
        """Создать outbox таблицу и индекс если не существуют."""
        async with pool.acquire() as conn:
            await conn.execute(_OUTBOX_DDL)
            await conn.execute(_OUTBOX_INDEX_DDL)
        logger.info("Outbox table ready")

    async def process(
        self,
        conn: asyncpg.Connection[Any],
        payload: FanOutPayloadMsg,
    ) -> None:
        """Проверить все правила против payload, записать уведомления в outbox."""
        logger.debug(
            "OutboxWriter.process called tables={tables}",
            tables=list(payload.tables.keys()),
        )

        for rule in self._rules:
            table_batch = payload.tables.get(rule.table)
            if table_batch is None:
                logger.debug(
                    "OutboxWriter rule skip — table not in payload table={table}",
                    table=rule.table,
                )
                continue

            logger.debug(
                "OutboxWriter matched table={table} upserts={upserts} deletes={deletes} rule_ops={ops}",
                table=rule.table,
                upserts=len(table_batch.upserts),
                deletes=len(table_batch.deletes),
                ops=list(rule.ops),
            )

            count = 0
            for record in table_batch.upserts:
                op = record.get("__op", CdcOp.CREATE)
                logger.debug(
                    "OutboxWriter record __op={op} keys={keys} raw={raw}",
                    op=op,
                    keys=list(record.keys()),
                    raw=record,
                )
                if op not in rule.ops:
                    logger.debug(
                        "OutboxWriter skip — op={op} not in {ops}",
                        op=op,
                        ops=list(rule.ops),
                    )
                    continue
                notification = OutboxNotification(
                    message_data=MessageData(
                        message_event=MessageEvent.op_mapper(op),
                        message_type=rule.table,
                    ),
                    payload={k: v for k, v in record.items() if not k.startswith("__")},
                )

                payload_bytes = self._encoder.encode(notification)
                logger.debug(
                    "OutboxWriter inserting id will be assigned queue={queue} payload_size={size}",
                    queue=rule.queue_name,
                    size=len(payload_bytes),
                )
                await conn.execute(
                    _OUTBOX_INSERT,
                    rule.queue_name,
                    payload_bytes.decode("utf-8"),
                )
                count += 1

            if count > 0:
                logger.info(
                    "Outbox notifications written count={count} table={table}",
                    count=count,
                    table=rule.table,
                )
            else:
                logger.debug(
                    "OutboxWriter no matching records for table={table}",
                    table=rule.table,
                )
