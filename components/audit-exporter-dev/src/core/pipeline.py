"""Per-source poll → write → ack composition for the export pipeline."""

import time

from loguru import logger
from pydantic import BaseModel, ConfigDict

from src.clickhouse.client import ClickHouseClient, ClickHouseWriteOutcome, derive_dedup_token
from src.core.config import SourceName
from src.core.state import BootstrapRuntimeState
from src.db.source_connections import (
    AcknowledgementOutcome,
    PostgresSourceReader,
    SourcePollResult,
)


class ProcessSourceResult(BaseModel):
    """Structured outcome from one poll → write → ack cycle for a single source."""

    model_config = ConfigDict(frozen=True)

    source_name: SourceName
    phase_reached: str
    poll_result: SourcePollResult | None
    write_outcome: ClickHouseWriteOutcome | None
    ack_outcome: AcknowledgementOutcome | None


async def process_source(
    reader: PostgresSourceReader,
    ch_client: ClickHouseClient,
    batch_size: int,
    state: BootstrapRuntimeState,
    *,
    cycle_id: str | None = None,
) -> ProcessSourceResult:
    """Execute one poll → write → ack cycle for a single source.

    Gates acknowledgement strictly on ``ClickHouseWriteOutcome.ok``.
    Captures expected failure paths (CH write failure, ack failure) in the
    returned result rather than raising.
    """
    source_name = reader.source_name
    poll_logger = logger.bind(cycle_id=cycle_id, source_name=source_name.value)

    poll_logger.debug("poll_start", batch_size=batch_size)
    poll_start = time.monotonic()
    try:
        events, poll_result = await reader.poll(batch_size=batch_size)
        state.record_source_poll_success(poll_result)
    except Exception as exc:
        duration_ms = round((time.monotonic() - poll_start) * 1000, 1)
        poll_logger.error("poll_failed", error=str(exc), duration_ms=duration_ms)
        state.record_source_poll_failure(source_name, str(exc))
        raise
    duration_ms = round((time.monotonic() - poll_start) * 1000, 1)

    if poll_result.row_count == 0:
        poll_logger.debug("poll_empty", duration_ms=duration_ms)
        return ProcessSourceResult(
            source_name=source_name,
            phase_reached="poll_empty",
            poll_result=poll_result,
            write_outcome=None,
            ack_outcome=None,
        )

    poll_logger.info(
        "poll_complete",
        rows_polled=poll_result.row_count,
        duration_ms=duration_ms,
        highest_timestamp=str(poll_result.highest_seen_timestamp),
        highest_outbox_id=str(poll_result.highest_seen_outbox_id),
    )

    dedup_token = derive_dedup_token(events)
    poll_logger.info(
        "write_start",
        row_count=poll_result.row_count,
        dedup_token=dedup_token[:12],
    )
    write_start = time.monotonic()
    write_outcome = await ch_client.insert_exported_events(events)
    write_duration_ms = round((time.monotonic() - write_start) * 1000, 1)
    state.record_clickhouse_write(write_outcome)

    if not write_outcome.ok:
        poll_logger.error(
            "write_failed",
            row_count=write_outcome.row_count,
            error=write_outcome.error_message,
            duration_ms=write_duration_ms,
        )
        return ProcessSourceResult(
            source_name=source_name,
            phase_reached="write_failed",
            poll_result=poll_result,
            write_outcome=write_outcome,
            ack_outcome=None,
        )

    poll_logger.info(
        "write_complete",
        rows_written=write_outcome.row_count,
        duration_ms=write_duration_ms,
        table_name=write_outcome.table,
    )

    outbox_ids = [event.outbox_id for event in events]
    poll_logger.info("ack_start", outbox_ids_count=len(outbox_ids))
    ack_start = time.monotonic()
    ack_outcome = await reader.acknowledge_rows(outbox_ids)
    ack_duration_ms = round((time.monotonic() - ack_start) * 1000, 1)
    state.record_acknowledgement(ack_outcome)

    if not ack_outcome.ok:
        poll_logger.error(
            "ack_failed",
            outbox_ids_count=len(outbox_ids),
            error=ack_outcome.error_message,
            duration_ms=ack_duration_ms,
        )
    else:
        poll_logger.info(
            "ack_complete",
            rows_acknowledged=ack_outcome.acknowledged_count,
            duration_ms=ack_duration_ms,
        )
        if ack_outcome.acknowledged_count != len(outbox_ids):
            poll_logger.warning(
                "ack_mismatch",
                outbox_ids_count=len(outbox_ids),
                rows_acknowledged=ack_outcome.acknowledged_count,
            )

    phase = "completed" if ack_outcome.ok else "ack_failed"
    return ProcessSourceResult(
        source_name=source_name,
        phase_reached=phase,
        poll_result=poll_result,
        write_outcome=write_outcome,
        ack_outcome=ack_outcome,
    )
