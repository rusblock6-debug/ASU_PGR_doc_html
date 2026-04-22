"""Background polling loop for multi-source audit export orchestration."""

import asyncio
import time
import uuid

from loguru import logger

from src.core.pipeline import process_source
from src.core.state import BootstrapRuntimeState


async def run_polling_loop(
    state: BootstrapRuntimeState,
    interval_seconds: float,
) -> None:
    """Poll all configured sources in sequence, isolating per-source failures.

    Runs indefinitely until cancelled via ``asyncio.CancelledError`` (the
    normal shutdown signal sent from the lifespan ``finally`` block).

    Each source is processed inside its own ``try/except Exception`` so that
    a failure in one source never blocks the remaining sources in the cycle.
    ``asyncio.CancelledError`` is intentionally **not** caught — it must
    propagate to stop the loop cleanly on shutdown.
    """
    if state.settings is None or state.clickhouse_client is None:
        msg = "run_polling_loop requires fully initialized state (settings and clickhouse_client)"
        raise RuntimeError(msg)

    settings = state.settings
    ch_client = state.clickhouse_client

    try:
        while True:
            # Sleep first: allows the system to stabilize after startup and
            # prevents a thundering-herd poll immediately on launch.
            await asyncio.sleep(interval_seconds)

            cycle_id = str(uuid.uuid4())
            cycle_start = time.monotonic()
            batch_size = settings.source_poll_batch_size

            cycle_logger = logger.bind(cycle_id=cycle_id)

            sources_succeeded = 0
            sources_failed = 0
            total_rows = 0

            for source_name, reader in state.postgres_readers.items():
                source_logger = cycle_logger.bind(source_name=source_name)
                try:
                    result = await process_source(
                        reader,
                        ch_client,
                        batch_size,
                        state,
                        cycle_id=cycle_id,
                    )
                    sources_succeeded += 1
                    row_count = result.poll_result.row_count if result.poll_result else 0
                    total_rows += row_count
                    if result.phase_reached != "poll_empty":
                        source_logger.info(
                            "source_cycle_complete",
                            phase_reached=result.phase_reached,
                            rows=row_count,
                        )
                except Exception:
                    sources_failed += 1
                    source_logger.error(
                        "source_cycle_failed",
                        exc_info=True,
                    )

            state.update_phase_from_runtime_health()

            cycle_duration_ms = round((time.monotonic() - cycle_start) * 1000, 1)
            if total_rows > 0 or sources_failed > 0:
                cycle_logger.info(
                    "cycle_end",
                    sources_succeeded=sources_succeeded,
                    sources_failed=sources_failed,
                    total_rows=total_rows,
                    cycle_duration_ms=cycle_duration_ms,
                )
    finally:
        logger.info("polling_loop_stopped")
