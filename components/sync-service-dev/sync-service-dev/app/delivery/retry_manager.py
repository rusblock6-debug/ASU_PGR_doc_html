import asyncio
import logging
import time
from typing import Awaitable, Callable

from app.models.types import NanoID
from app.protocol.disassembler import Disassembler
from app.state.locks_store import LocksStore

logger = logging.getLogger("delivery.retry")


class RetryManager:
    """Manages retransmission of failed chunks."""

    def __init__(self, locks_store: LocksStore, disassembler: Disassembler) -> None:
        """Initialize retry manager."""

        self.locks_store = locks_store
        self.disassembler = disassembler

        self.retry_queue: dict[NanoID, RetryEntry] = {}
        self.retry_task: asyncio.Task | None = None

        self._retry_loop_delay: float = 0.1

    async def start(self) -> None:
        """Start retry background task."""
        self.retry_task = asyncio.create_task(self._retry_loop())

    async def stop(self) -> None:
        """Stop retry background task."""
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass

    async def schedule_retry(
        self,
        msg_id: NanoID,
        receiver_id: str,
        total_chunks: int,
        retry_max_attempts: int,
        retry_backoff_base: int,
        retry_multiplier: int,
        retry_max_delay: int,
        callback: Callable[[NanoID, str, int], Awaitable[None]],
        failure_callback: Callable[[NanoID], Awaitable[None]] | None = None,
    ) -> None:
        """Schedule a chunk for retry.

        Args:
            msg_id: Message ID
            receiver_id: Receiver ID
            total_chunks: Total number of chunks in message
            retry_max_attempts: Max retry attempts
            retry_backoff_base: Retry backoff base in ms
            retry_multiplier: Retry multiplier for exponential backoff
            retry_max_delay: Maximum retry delay in ms
            callback: Callback to execute when retrying this chunk
            failure_callback: Optional callback to execute when giving up on this message
        """
        if msg_id not in self.retry_queue:
            self.retry_queue[msg_id] = RetryEntry(
                msg_id, receiver_id, total_chunks, retry_max_attempts, retry_backoff_base,
                retry_multiplier, retry_max_delay, callback, failure_callback
            )
            logger.debug(f"[{msg_id}] Created retry entry with {total_chunks} total chunks")

    def remove_from_queue(self, msg_id: NanoID) -> None:
        """Remove message from retry queue."""
        if msg_id in self.retry_queue:
            del self.retry_queue[msg_id]
            logger.debug(f"[{msg_id}] Msg removed from retry queue")
        else:
            logger.warning(f"[{msg_id}] Msg not found in retry queue, hence cannot be removed")

    def should_complete(self, msg_id: NanoID) -> bool:
        """Check if we should complete retrying this message."""
        if msg_id not in self.retry_queue:
            return False
        message = self.disassembler.get(msg_id)
        if message is not None and message.is_sending:
            return False
        return True

    def complete(self, msg_id: NanoID) -> None:
        """Complete retrying this message."""
        self.remove_from_queue(msg_id)

    def should_give_up(self, msg_id: NanoID, time_since_last: float) -> bool:
        """Check if we should give up retrying this message."""
        if msg_id not in self.retry_queue:
            return True
        entry = self.retry_queue[msg_id]
        if entry.retry_max_attempts == -1:
            return False
        if entry.retry_max_attempts == 0:
            return time_since_last >= entry.backoff_seconds
        return entry.retry_count >= entry.retry_max_attempts and time_since_last >= entry.backoff_seconds

    async def give_up(self, msg_id: NanoID, entry: "RetryEntry") -> None:
        """Give up retrying this message."""
        if entry.failure_callback:
            try:
                await entry.failure_callback(msg_id)
            except Exception:
                logger.exception(f"[{msg_id}] Error in failure callback")
        self.remove_from_queue(msg_id)

    async def terminate(self, msg_id: NanoID) -> None:
        """Enforce to give up message retry attempts."""
        lock_key = f"{self.locks_store.retry_prefix}:{msg_id}"
        await self.locks_store.acquire_lock(lock_key)
        try:
            self.remove_from_queue(msg_id)
        finally:
            self.locks_store.release_lock(lock_key)
        logger.warning(f"[{msg_id}] Terminated msg retry attempts")

    async def _retry_loop(self) -> None:
        """Background task that processes retries."""
        # TODO: parallelize RetryEntry handling (private coro and/or loop for each one?)
        while True:
            try:
                for msg_id, entry in list(self.retry_queue.items()):

                    lock_key = f"{self.locks_store.retry_prefix}:{msg_id}"
                    await self.locks_store.acquire_lock(lock_key)

                    try:
                        current_time = time.monotonic()
                        time_since_last = current_time - entry.last_retry_time

                        # Check if we should complete retrying this message. Perform before actual retry because we want
                        # to wait for ACKs caused by the previous one.
                        if self.should_complete(msg_id):
                            logger.debug(f"[{msg_id}] Completing msg after {entry.retry_count_str} retry attempts")
                            self.complete(msg_id)
                            continue

                        # Check if we should give up on this message. Perform before actual retry because we want
                        # to wait for ACKs caused by the very last one. If they are still not here - then give up
                        if self.should_give_up(msg_id, time_since_last):
                            logger.error(f"[{msg_id}] Giving up on msg after {entry.retry_count_str} retry attempts")
                            await self.give_up(msg_id, entry)
                            continue

                        # Check if it's time to retry this message
                        if time_since_last >= entry.backoff_seconds and entry.retry_max_attempts != 0:
                            # Trigger retries for pending chunks
                            indices_to_retry = self.disassembler.get_unacked_indices(msg_id)
                            logger.debug(
                                f"[{msg_id}] Retry check: time_since_last={time_since_last:.2f}s, "
                                f"backoff={entry.backoff_seconds:.2f}s, indices_to_retry={len(indices_to_retry)}"
                            )
                            if indices_to_retry:
                                await self._retry_chunks(entry, indices_to_retry)
                                # Increment retry count after attempting retries
                                entry.retry_count += 1
                                entry.last_retry_time = current_time
                                # Increase backoff for next time
                                entry.increase_backoff()
                                logger.debug(
                                    f"[{msg_id}] Retried {len(indices_to_retry)} chunks, "
                                    f"attempt {entry.retry_count_str}"
                                )
                            else:
                                logger.warning(
                                    f"[{msg_id}] Somehow no chunks to retry, so forced to give up "
                                    f"after {entry.retry_count_str} retry attempts"
                                )
                                await self.give_up(msg_id, entry)
                                continue

                    finally:
                        self.locks_store.release_lock(lock_key)

                await asyncio.sleep(self._retry_loop_delay)
            except asyncio.CancelledError:
                logger.debug("Retry loop cancelled")
                raise
            except Exception:
                logger.exception("Retry loop error")

    async def _retry_chunks(self, entry: "RetryEntry", chunk_indices: set[int]) -> None:

        async def _retry_chunk(index: int) -> None:
            """Retry a single chunk with error handling."""
            try:
                await entry.callback(entry.msg_id, entry.receiver_id, index)
            except Exception:
                logger.exception(f"[{entry.msg_id}] Error retrying chunk {index} (total: {entry.total_chunks})")
            else:
                logger.debug(f"[{entry.msg_id}] Retried chunk {index} (total: {entry.total_chunks})")

        await asyncio.gather(*[
            _retry_chunk(index)
            for index in chunk_indices
        ], return_exceptions=True)


class RetryEntry:
    """Entry for a message in the retry queue."""

    def __init__(
        self,
        msg_id: NanoID,
        receiver_id: str,
        total_chunks: int,
        retry_max_attempts: int,
        retry_backoff_base: int,
        retry_multiplier: int,
        retry_max_delay: int,
        callback: Callable[[NanoID, str, int], Awaitable[None]],
        failure_callback: Callable[[NanoID], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize retry entry."""
        self.msg_id = msg_id
        self.receiver_id = receiver_id
        self.total_chunks = total_chunks
        self.callback = callback
        self.failure_callback = failure_callback

        self.retry_max_attempts = retry_max_attempts
        self.retry_backoff_base = retry_backoff_base
        self.retry_multiplier = retry_multiplier
        self.retry_max_delay = retry_max_delay

        # Initialize backoff for first retry
        self.retry_count = 0
        self.backoff_ms = min(retry_backoff_base, retry_max_delay)
        self.initial_time = time.monotonic()
        self.last_retry_time = self.initial_time

    @property
    def backoff_seconds(self):
        return self.backoff_ms / 1000

    def increase_backoff(self) -> None:
        """Increase backoff for next retry using exponential formula."""
        next_delay = self.retry_backoff_base * (self.retry_multiplier ** self.retry_count)
        self.backoff_ms = min(next_delay, self.retry_max_delay)

    @property
    def retry_count_str(self) -> str:
        """Get retry count string."""
        if self.retry_max_attempts > -1:
            max_str = self.retry_max_attempts
        else:
            max_str = "∞"
        return f"{self.retry_count}/{max_str}"
