import asyncio
import logging
from typing import Awaitable, Callable

import redis.asyncio as redis
from fastnanoid import generate
from redis.exceptions import ResponseError

from app.delivery.retry_manager import RetryManager
from app.models.schemas import DeliveryParams
from app.models.types import NanoID
from app.mqtt.client import MQTTClient
from app.protocol.codec import Chunk
from app.protocol.disassembler import Disassembler, MessageOut
from app.protocol.reassembler import MessageIn, Reassembler
from app.settings import settings
from app.state.events_store import EventsStore
from app.state.locks_store import LocksStore

logger = logging.getLogger("delivery")


class DeliveryManager:
    """Manages at-least-once message delivery."""

    SENDING_PREFIX = "delivery:sending"
    "Prefix for redis key of sending msg data dump `{SENDING_PREFIX}:{msg_id}`"
    SENT_PREFIX = "delivery:sent"
    "Prefix for redis key of sent msg data dump `{SENT_PREFIX}:{msg_id}`"
    FAILED_PREFIX = "delivery:failed"
    "Prefix for redis key of failed msg data dump `{FAILED_PREFIX}:{msg_id}`"
    RECEIVED_PREFIX = "delivery:received"
    "Prefix for redis key of received msg data dump `{RECEIVED_PREFIX}:{msg_id}`"
    DEDUP_PREFIX = "delivery:dedup"
    "Prefix for deduplication redis key `{DEDUP_PREFIX}:{msg_id}`"

    def __init__(
        self,
        redis_client: redis.Redis,
        mqtt_client: MQTTClient,
        retry_manager: RetryManager,
        reassembler: Reassembler,
        locks_store: LocksStore,
        events_store: EventsStore,
        disassembler: Disassembler,
    ) -> None:
        """Initialize delivery manager."""

        self.redis = redis_client
        self.mqtt_client = mqtt_client
        self.retry_manager = retry_manager
        self.reassembler = reassembler
        self.locks_store = locks_store
        self.events_store = events_store
        self.disassembler = disassembler

        self.message_arrival_callbacks: list[Callable[[NanoID, bytes], Awaitable[None]]] = []

        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the delivery manager."""

        if not settings.multi_replica_mode:
            await self.subscribe_to_instance()

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started cleanup task")

    async def stop(self) -> None:
        """Stop the delivery manager."""

        if not settings.multi_replica_mode:
            await self.unsubscribe_from_instance()

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                logger.debug("Cleanup loop cancelled")
            logger.info("Stopped cleanup task")

    async def subscribe_to_instance(self, instance_id: str = "+") -> None:

        data_topic = f"sync/{settings.instance_id}/data/{instance_id}"
        await self.mqtt_client.subscribe(data_topic, self._handle_data_chunk)
        logger.info(f"Subscribed to data topic: {data_topic}")

        ack_topic = f"sync/{settings.instance_id}/ack/{instance_id}"
        await self.mqtt_client.subscribe(ack_topic, self._handle_ack_chunk)
        logger.info(f"Subscribed to ack topic: {ack_topic}")

    async def unsubscribe_from_instance(self, instance_id: str = "+") -> None:

        data_topic = f"sync/{settings.instance_id}/data/{instance_id}"
        await self.mqtt_client.unsubscribe(data_topic)
        logger.info(f"Unsubscribed from data topic: {data_topic}")

        ack_topic = f"sync/{settings.instance_id}/ack/{instance_id}"
        await self.mqtt_client.unsubscribe(ack_topic)
        logger.info(f"Unsubscribed from ack topic: {ack_topic}")

    async def _handle_data_chunk(self, topic: str, payload: bytes) -> None:
        """Handle incoming data chunks."""
        try:
            topic_parts = topic.split("/")
            sender_id = topic_parts[3]
            chunk = Chunk.from_bytes(payload)
            if chunk.is_ack:
                logger.error(f"[{chunk.msg_id}] Received ACK chunk by data topic")
                return
            await self.receive_chunk(chunk, sender_id)
        except Exception:
            logger.exception("Error handling data chunk")

    async def _handle_ack_chunk(self, topic: str, payload: bytes) -> None:
        """Handle incoming ACK chunks."""
        try:
            topic_parts = topic.split("/")
            receiver_id = topic_parts[3]
            ack_chunk = Chunk.from_bytes(payload)
            if not ack_chunk.is_ack:
                logger.error(f"[{ack_chunk.msg_id}] Received non-ACK chunk by ack topic")
                return
            await self.receive_ack(ack_chunk, receiver_id)
        except Exception:
            logger.exception("Error handling ACK chunk")

    def on_arrival(self, callback: Callable[[NanoID, bytes], Awaitable[None]]) -> None:
        self.message_arrival_callbacks.append(callback)


    async def send_message(self, data: bytes, params: DeliveryParams, msg_id: NanoID | None = None) -> NanoID:
        """Store a message in Redis and send it with specified delivery guarantee."""

        if len(data) > settings.max_size:
            raise ValueError(f"Msg size {len(data)} exceeds maximum {settings.max_size}")

        # Alphabet supposed to contain only 1 byte UTF-8 chars
        msg_id = NanoID(msg_id or generate(size=settings.id_length))
        logger.debug(f"[{msg_id}] Preparing msg for {params.receiver_id} ({len(data)} bytes)")

        if settings.debug_mode:
            await self.redis.set(f"{self.SENDING_PREFIX}:{msg_id}", data, ex=settings.common_redis_ttl)
        message = self.disassembler.add(msg_id, data, params)
        logger.info(
            f"[{msg_id}] Sending msg to {params.receiver_id} "
            f"({message.total_size} bytes, {message.total_chunks} chunks)"
        )

        await self._dispatch_message(
            message,
            params.receiver_id,
            params.retry_max_attempts,
            params.retry_backoff_base,
            params.retry_multiplier,
            params.retry_max_delay,
        )
        logger.info(f"[{msg_id}] Dispatched msg for receiver_id {params.receiver_id}")

        return msg_id

    async def _dispatch_message(
        self,
        message: MessageOut,
        receiver_id: str,
        retry_max_attempts: int,
        retry_backoff_base: int,
        retry_multiplier: int,
        retry_max_delay: int,
    ) -> None:

        async def _dispatch_chunk(chunk: Chunk) -> None:
            """Send chunk and ensure retry scheduling even on failure."""
            try:
                await self._send_chunk(chunk, receiver_id)
            except Exception:
                logger.exception(f"[{chunk.msg_id}] Failed to send chunk {chunk.index} (total: {chunk.total})")
            else:
                logger.debug(f"[{chunk.msg_id}] Sent chunk {chunk.index} (total: {chunk.total})")

        try:
            await asyncio.gather(*[
                _dispatch_chunk(chunk)
                for chunk in message.chunks_list
            ], return_exceptions=True)
        finally:
            await self.retry_manager.schedule_retry(
                message.msg_id,
                receiver_id,
                message.total_chunks,
                retry_max_attempts,
                retry_backoff_base,
                retry_multiplier,
                retry_max_delay,
                callback=self._retry_chunk,
                failure_callback=self._complete_message_failure,
            )

    async def _retry_chunk(self, msg_id: NanoID, receiver_id: str, index: int) -> None:
        """Callback for retrying a chunk with error handling."""

        try:
            chunk = self.disassembler.get_chunk(msg_id, index)
            if chunk is None:
                raise ValueError(f"[{msg_id}] No stored data for chunk {index} during retry")
            await self._send_chunk(chunk, receiver_id)

        except Exception:
            logger.exception(f"[{msg_id}] Error in retry callback for chunk {index}")

    async def _send_chunk(self, chunk: Chunk, receiver_id: str) -> None:
        """Send a single chunk."""
        topic = f"sync/{receiver_id}/data/{settings.instance_id}"
        payload = chunk.to_bytes()
        await self.mqtt_client.publish(topic, payload)

    async def _complete_message_failure(self, msg_id: NanoID) -> None:
        """Mark a message as failed and clean up resources."""
        logger.warning(f"[{msg_id}] Marking msg as failed")
        # Notify all waiters about result
        self.events_store.set_failure(msg_id)
        # Delete stored chunks to spare memory
        self.disassembler.delete_chunks(msg_id)
        if settings.debug_mode:
            from_str = f"{self.SENDING_PREFIX}:{msg_id}"
            to_str = f"{self.FAILED_PREFIX}:{msg_id}"
            try:
                await self.redis.rename(from_str, to_str)
            except ResponseError:
                logger.debug(f"[{msg_id}] Failed to rename msg from {from_str} to {to_str}", exc_info=True)
        logger.debug(f"[{msg_id}] Msg marked as failed and cleaned up")


    async def receive_chunk(self, chunk: Chunk, sender_id: str) -> None:
        """Receive and process a data chunk.

        Args:
            chunk: The received chunk
            sender_id: Sender's instance ID
        """

        logger.debug(
            f"[{chunk.msg_id}] Received chunk {chunk.index} (total: {chunk.total}, sender: {sender_id})"
        )

        lock_key = f"{self.locks_store.receive_prefix}:{chunk.msg_id}"
        await self.locks_store.acquire_lock(lock_key)

        try:
            message = self.reassembler.get(chunk.msg_id)
            if not message:
                message = MessageIn(msg_id=chunk.msg_id, total_chunks=chunk.total)
                self.reassembler.add(message)

            message.add_chunk(chunk)
            if message.are_all_chunks_in_place:
                message_data = message.assemble()
                if settings.debug_mode:
                    await self.redis.set(
                        f"{self.RECEIVED_PREFIX}:{chunk.msg_id}", message_data, ex=settings.common_redis_ttl
                    )
                logger.info(
                    f"[{chunk.msg_id}] Msg fully received and stored "
                    f"({len(message_data)} bytes, {chunk.total} chunks)"
                )

            if message.data is not None and not message.are_callbacks_called:

                logger.debug(f"[{chunk.msg_id}] Calling callbacks")
                for callback in self.message_arrival_callbacks:
                    try:
                        await callback(chunk.msg_id, message.data)
                    except Exception:
                        logger.error(f"[{chunk.msg_id}] Error in arrival callback {callback.__name__}")
                        raise
                message.are_callbacks_called = True
                message.spare_memory()

            # Send ACK back
            # TODO: option to disable acking for configs with retry_max_attempts=0
            received_indices = message.get_chunk_indices()
            await self._send_ack(chunk.msg_id, chunk.total, sender_id, received_indices)

        finally:
            self.locks_store.release_lock(lock_key)

    async def _send_ack(
        self, msg_id: NanoID, total_chunks: int, sender_id: str, received_indices: set[int]
    ) -> None:
        """Send ACK for received chunks using flexible format.

        Args:
            msg_id: Message ID
            total_chunks: Total number of chunks
            sender_id: Sender's instance ID
            received_indices: Set of received chunk indices
        """
        # TODO: buffer and merge outgoing acks for specific message
        ack = Chunk.create_ack(msg_id, received_indices, total_chunks)
        topic = f"sync/{sender_id}/ack/{settings.instance_id}"
        payload = ack.to_bytes()
        await self.mqtt_client.publish(topic, payload)
        logger.debug(
            f"[{msg_id}] Sent ACK to {sender_id} with {len(received_indices)}/{total_chunks} chunks"
        )

    async def receive_ack(self, ack_chunk: Chunk, receiver_id: str) -> None:
        """Handle incoming ACK chunk with flexible format support."""

        acked = ack_chunk.get_acked_indices()
        logger.debug(
            f"[{ack_chunk.msg_id}] Received ACK for {len(acked)} chunks "
            f"(total: {ack_chunk.total}, receiver: {receiver_id})"
        )

        lock_key = f"{self.locks_store.retry_prefix}:{ack_chunk.msg_id}"
        await self.locks_store.acquire_lock(lock_key)

        try:
            message = self.disassembler.get(ack_chunk.msg_id)
            if message is None:
                logger.warning(f"[{ack_chunk.msg_id}] Received ACK for unknown msg")
                return
            elif message.is_sent:
                logger.debug(f"[{ack_chunk.msg_id}] Received ACK for sent msg")
                return
            elif message.is_failed:
                logger.debug(f"[{ack_chunk.msg_id}] Received ACK for failed msg")
                return

            # Mark all acked chunks
            # TODO: add timestamp check to discard belated acks
            # (to eliminate probability of undesirable rollbacks of acked chunks set)
            gained = acked - message.acked
            lost = message.acked - acked
            message.acked = acked
            logger.debug(
                f"[{ack_chunk.msg_id}] Acked chunks change +{len(gained)} -{len(lost)} ={len(acked)}/{ack_chunk.total}"
            )

            # Check if all chunks acknowledged
            if len(message.acked) == ack_chunk.total:
                await self._complete_message_success(ack_chunk.msg_id, ack_chunk.total)

        finally:
            self.locks_store.release_lock(lock_key)

    async def _complete_message_success(self, msg_id: NanoID, total_chunks: int) -> None:
        """Mark message as complete."""
        logger.info(f"[{msg_id}] Msg fully acknowledged ({total_chunks} chunks)")
        # Notify all waiters about result
        self.events_store.set_success(msg_id)
        # Delete stored chunks to spare memory
        self.disassembler.delete_chunks(msg_id)
        if settings.debug_mode:
            from_str = f"{self.SENDING_PREFIX}:{msg_id}"
            to_str = f"{self.SENT_PREFIX}:{msg_id}"
            try:
                await self.redis.rename(from_str, to_str)
            except ResponseError:
                logger.debug(f"[{msg_id}] Failed to rename msg from {from_str} to {to_str}", exc_info=True)


    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale Reassembler and Disassembler messages."""

        while True:
            await asyncio.sleep(settings.cleanup_interval_seconds)

            # 1. Clean Reassembler messages older than timeout
            try:
                assembled_mids, incomplete_mids = self.reassembler.clean(settings.dedup_redis_ttl)
                if assembled_mids:
                    logger.info(f"Cleaned up {len(assembled_mids)} stale assembled Reassembler messages")
                else:
                    logger.debug("No stale assembled Reassemble messages were found")
                if incomplete_mids:
                    logger.warning(f"Cleaned up {len(incomplete_mids)} stale incomplete Reassembler messages")
                else:
                    logger.debug("No stale incomplete Reassemble messages were found")
            except Exception:
                logger.exception("Error in stale Reassembler messages cleanup")

            # 2. Clean Disassembler messages older than timeout
            try:
                sent_mids, failed_mids = self.disassembler.clean(settings.dedup_redis_ttl)
                if sent_mids:
                    logger.info(f"Cleaned up {len(sent_mids)} stale sent Disassembler messages")
                else:
                    logger.debug("No stale sent Disassembler messages were found")
                if failed_mids:
                    logger.warning(f"Cleaned up {len(failed_mids)} stale failed Disassembler messages:")
                else:
                    logger.debug("No stale failed Disassembler messages were found")
            except Exception:
                logger.exception("Error in stale Disassembler messages cleanup")
