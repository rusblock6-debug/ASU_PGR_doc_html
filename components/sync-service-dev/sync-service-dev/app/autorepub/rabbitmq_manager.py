import asyncio
import logging
from dataclasses import dataclass
from functools import cached_property

import aio_pika
import redis.asyncio as redis
from fastnanoid import generate

from app.delivery.delivery_manager import DeliveryManager
from app.delivery.retry_manager import RetryManager
from app.models.schemas import AutorepubConfig, DeliveryParams
from app.models.types import AutorepubConfigType, NanoID
from app.settings import settings
from app.state.events_store import EventsStore

from .config_manager import AutorepubConfigManager
from .consts import PAYLOAD_SEPARATOR, TOTAL_SEPARATORS  # DEBUG_PREFIX

logger = logging.getLogger("autorepub.rabbit")

SOURCE_QUEUE_POSTFIX = "src"
TARGET_QUEUE_POSTFIX = "dst"
DEAD_QUEUE_POSTFIX = "dlq"


@dataclass
class Channel:
    pika_obj: aio_pika.RobustChannel
    queues_count: int = 0

    @classmethod
    async def init_new(cls, connection: aio_pika.RobustConnection) -> "Channel":
        channel: aio_pika.RobustChannel = await connection.channel()  # type: ignore
        await channel.set_qos(prefetch_count=1)
        return cls(pika_obj=channel)

    async def declare_pika_queue(self, name: str, name_dlq: str | None = None) -> aio_pika.RobustQueue:
        if name_dlq:
            args = {
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": name_dlq,
                # "x-single-active-consumer": True,
                # "x-consumer-timeout": 60_000,
            }
            await self.pika_obj.declare_queue(name_dlq, durable=True)
        else:
            args = None
        pika_queue: aio_pika.RobustQueue = await self.pika_obj.declare_queue(
            name, durable=True, arguments=args,
        )  # type: ignore
        self.queues_count += 1
        return pika_queue

    async def publish(self, queue_name: str, payload: bytes, message_id: str | None) -> None:
        await self.pika_obj.default_exchange.publish(
            aio_pika.Message(
                payload,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=message_id,
            ),
            routing_key=queue_name,
        )


@dataclass
class QueueSrc:
    config: AutorepubConfig
    target_instance_id: str
    pika_obj: aio_pika.RobustQueue | None = None
    asyncio_task: asyncio.Task | None = None
    stopped: bool = False

    @cached_property
    def name_root(self):
        return f"{settings.instance_id}.{self.target_instance_id}.{self.config.queue_name}"

    @cached_property
    def name(self):
        return f"{self.name_root}.{SOURCE_QUEUE_POSTFIX}"

    @cached_property
    def name_dlq(self):
        return f"{self.name_root}.{DEAD_QUEUE_POSTFIX}"

    @cached_property
    def name_dst(self):
        return f"{self.name_root}.{TARGET_QUEUE_POSTFIX}"

    @property
    def channel(self) -> aio_pika.RobustChannel | None:
        if not self.pika_obj:
            return None
        return self.pika_obj.channel  # type: ignore


class AutorepubRabbitMQManager:
    """Manages autorepub message transfer between RabbitMQ queues on different instances."""

    PAYLOAD_FORMAT_FLAG = b"r"
    DEDUP_PREFIX = "autorepub:dedup"
    "Prefix for deduplication redis key `{DEDUP_PREFIX}:{dedup_id}`"

    def __init__(
        self,
        redis_client: redis.Redis,
        config_manager: AutorepubConfigManager,
        delivery_manager: DeliveryManager,
        retry_manager: RetryManager,
        events_store: EventsStore,
    ) -> None:
        """Initialize autorepub manager."""

        self.redis: redis.Redis = redis_client
        self.config_manager = config_manager
        self.delivery_manager = delivery_manager
        self.retry_manager = retry_manager
        self.events_store = events_store

        self.connection: aio_pika.RobustConnection | None = None
        self._subscribe_task: asyncio.Task | None = None
        self._channels_src: dict[str, Channel] = {}
        self._channel_dst: Channel | None = None
        self._queues_src: dict[str, QueueSrc] = {}
        self._queues_dst: dict[str, aio_pika.RobustQueue] = {}

        self._owned_instances: set[str] = set()

        self._subscription_loop_delay: float = 2.0

    async def start(self) -> None:
        """Start autorepub manager and subscribe to active configs."""

        logger.debug(f"Connecting to RabbitMQ at {settings.rabbitmq_dsn}")
        # Robust connection handles reconnects automatically
        self.connection = await aio_pika.connect_robust(
            settings.rabbitmq_dsn,
            fail_fast=False,
            reconnect_interval=1,
        )  # type: ignore
        logger.debug("Opened connection")
        self._channel_dst = await Channel.init_new(self.connection)  # type: ignore
        logger.debug("Established dst channel")

        # Create rabbit src queues for all configs (yeah, through dst channel)
        configs = self.config_manager.get_configs(type_=AutorepubConfigType.RABBITMQ)
        for config in configs:
            if not config.is_debug:
                for target_instance_id in config.target_instances_list:
                    queue_src = QueueSrc(config, target_instance_id)
                    await self._channel_dst.declare_pika_queue(queue_src.name, queue_src.name_dlq)
                    self._channel_dst.queues_count -= 1
                    logger.info(f"({queue_src.name}) Created src queue")

        # Subscribe only to active configs
        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.RABBITMQ, is_active=True)
        for config in active_configs:
            await self.subscribe_to_config(config)

        self._subscribe_task = asyncio.create_task(self._subscription_loop())

        logger.info("Autorepub manager started")

    async def stop(self) -> None:
        """Stop autorepub manager and cleanup."""

        if self._subscribe_task:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass
            self._subscribe_task = None

        logger.debug("Stopped subscription loop")

        if self._channel_dst:
            try:
                await self._channel_dst.pika_obj.close()
                logger.debug("Dst channel closed")
            except Exception:
                logger.exception("Error closing dst channel")
            finally:
                self._channel_dst = None

        await asyncio.gather(
            *[c.pika_obj.close() for c in self._channels_src.values()],
            return_exceptions=True
        )
        self._channels_src.clear()
        logger.debug("All src channels closed")

        if self.connection:
            try:
                await self.connection.close()
                logger.debug("Connection closed")
            except Exception:
                logger.exception("Error closing connection")
            finally:
                self.connection = None

        logger.info("Autorepub manager stopped")

    # ─────────────────────────────────────────────────────────────────────────
    # Loop tasks machinery
    # ─────────────────────────────────────────────────────────────────────────

    async def _subscription_loop(self) -> None:
        """Orchestrate channels, queues and consumer tasks"""

        if not self.connection or self.connection.is_closed:
            logger.error("Cannot run _subscription_loop: connection is unavailable")
            return

        queues_str = ", ".join(self._queues_src)
        if not queues_str:
            queues_str = "empty list"
        logger.debug(f"Setting up subscription loops for queues: {queues_str}")

        # Continuous monitoring and recovery loop
        while True:

            try:
                for queue_src in self._queues_src.values():
                    # Create tasks for new/failed queues
                    if not queue_src.asyncio_task and not queue_src.stopped:

                        if not queue_src.channel or queue_src.channel.is_closed:
                            # Open brand new channel if current is absent/closed
                            # (tried to reopen previously closed channels - they did not work properly)
                            channel_src = self._channels_src.get(queue_src.target_instance_id)
                            if not channel_src or channel_src.pika_obj.is_closed:
                                channel_src = await Channel.init_new(self.connection)
                                self._channels_src[queue_src.target_instance_id] = channel_src
                                logger.debug(f"({queue_src.name}) Established src channel")
                            else:
                                logger.debug(f"({queue_src.name}) Src channel already exists")

                            # Redeclare queue (did not even try to reuse after the fail with channels)
                            queue_src.pika_obj = await channel_src.declare_pika_queue(
                                queue_src.name, queue_src.name_dlq
                            )
                            logger.debug(f"({queue_src.name}) Declared src queue")

                        # Create actual asyncio task
                        queue_src.asyncio_task = asyncio.create_task(self._process_queue(queue_src))
                        logger.info(f"({queue_src.name}) Created queue task")

                    # Cancel tasks for stopped queues
                    elif queue_src.asyncio_task and queue_src.stopped:
                        # Not waiting here for task completion because it highly likely
                        # will end naturally after mandatory loop sleep
                        queue_src.asyncio_task.cancel()
                        logger.debug(f"({queue_src.name}) Cancelling queue task")

                await asyncio.sleep(self._subscription_loop_delay)

                # Check for completed tasks (cancelled or failed)
                for queue_name in list(self._queues_src):
                    queue_src = self._queues_src[queue_name]

                    if queue_src.asyncio_task and queue_src.asyncio_task.done():

                        # Some informative logs for different cases
                        if queue_src.asyncio_task.cancelled():
                            if queue_src.stopped:
                                logger.info(f"({queue_src.name}) Queue task has been cancelled")
                            else:
                                logger.warning(f"({queue_src.name}) Queue task has been cancelled unexpectedly")

                        else:
                            task_exc = queue_src.asyncio_task.exception()

                            if task_exc is None:
                                if queue_src.stopped:
                                    logger.info(f"({queue_src.name}) Queue task finished")
                                else:
                                    logger.warning(f"({queue_src.name}) Queue task finished unexpectedly")

                            else:
                                task_exc_repr = task_exc.__class__.__name__
                                if len(str(task_exc)):
                                    task_exc_repr = f"{task_exc_repr}: {task_exc}"
                                logger.error(
                                    f"({queue_src.name}) Queue task failed - {task_exc_repr}"
                                )

                        # Close and delete channel if it was its last task
                        channel_src = self._channels_src.get(queue_src.target_instance_id)
                        if channel_src:

                            if queue_src.stopped:
                                channel_src.queues_count -= 1

                            if channel_src.queues_count < 1:
                                await channel_src.pika_obj.close()
                                logger.debug(f"({queue_src.name}) Closed src channel")

                            if channel_src.pika_obj.is_closed:
                                del self._channels_src[queue_src.target_instance_id]
                                logger.debug(f"({queue_src.name}) Deleted src channel")

                        # Nullify task and queue objects. Delete only explicitly stopped queues,
                        # because we need to resurrect queue task if it was an unexpected demise
                        queue_src.asyncio_task = None
                        if queue_src.stopped:
                            del self._queues_src[queue_name]

            except asyncio.CancelledError:
                # Shutting down probably
                logger.debug("Subscription loop cancelled")
                # Cancel all remaining tasks
                tasks_to_wait = []
                for queue_src in self._queues_src.values():
                    if queue_src.asyncio_task:
                        queue_src.asyncio_task.cancel()
                        tasks_to_wait.append(queue_src.asyncio_task)
                # Wait for all tasks to finish cancelling
                await asyncio.gather(*tasks_to_wait, return_exceptions=True)
                logger.debug("All queue loops cancelled either")
                raise

            except Exception:
                logger.exception("Subscription loop error")

    async def _process_queue(self, queue_src: QueueSrc) -> None:
        """Process messages from a single queue."""

        if not queue_src.pika_obj:
            logger.error(f"Cannot run _process_queue for {queue_src.name}: queue not available")
            return
        if not queue_src.channel or queue_src.channel.is_closed:
            logger.error(f"Cannot run _process_queue for {queue_src.name}: channel not available")
            return

        async with queue_src.pika_obj.iterator() as queue_iter:

            while True:
                message = msg_id = None

                try:
                    # Iterating manually to have more control over consumer loop
                    message = await anext(queue_iter)
                    # Alphabet supposed to contain only 1 byte UTF-8 chars
                    msg_id = NanoID(generate(size=settings.id_length))
                    self.events_store.create(msg_id)
                    result = await self._handle_source_message(
                        queue_src.config, queue_src.name, msg_id, message.body, message.message_id
                    )
                    self.events_store.delete(msg_id)
                    if not result:
                        logger.warning(
                            f"({queue_src.name}) Failed to receive delivery confirmation of msg [{msg_id}]"
                        )
                        await message.reject()
                        continue

                    await message.ack()
                    logger.info(f"({queue_src.name}) Successfully confirmed delivery of msg [{msg_id}]")

                except asyncio.CancelledError:
                    if queue_src.stopped:
                        logger.debug(f"({queue_src.name}) Queue task cancellation due to stoppage")
                    else:
                        # Shutting down probably
                        logger.debug(f"({queue_src.name}) Queue task cancellation")
                    if msg_id:
                        await self.retry_manager.terminate(msg_id)
                        self.events_store.delete(msg_id)
                    if message and queue_src.channel and not queue_src.channel.is_closed:
                        await message.nack()
                    raise

                except (aio_pika.exceptions.ChannelClosed, aio_pika.exceptions.ChannelInvalidStateError):
                    if msg_id:
                        await self.retry_manager.terminate(msg_id)
                        self.events_store.delete(msg_id)
                    if queue_src.stopped:
                        logger.debug(f"({queue_src.name}) Expected channel closure due to stoppage")
                        break
                    else:
                        logger.exception(f"({queue_src.name}) Unexpected channel closure")
                        raise

                except StopAsyncIteration:
                    if msg_id:
                        await self.retry_manager.terminate(msg_id)
                        self.events_store.delete(msg_id)
                    if message:
                        await message.nack()
                    if queue_src.stopped:
                        logger.debug(f"({queue_src.name}) Expected iterator exhaustion due to stoppage")
                        break
                    else:
                        logger.exception(f"({queue_src.name}) Unexpected iterator exhaustion")
                        raise

                except Exception:
                    logger.exception(f"({queue_src.name}) Failed to properly handle msg")
                    if msg_id:
                        await self.retry_manager.terminate(msg_id)
                        self.events_store.delete(msg_id)
                    if message:
                        await message.nack()
                    raise

    # ─────────────────────────────────────────────────────────────────────────
    # Instance ownership (multi_replica_mode)
    # ─────────────────────────────────────────────────────────────────────────

    async def subscribe_to_instance(self, instance_id: str) -> None:
        self._owned_instances.add(instance_id)

        if self.is_suspended_instance(instance_id):
            return

        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.RABBITMQ, is_active=True)

        for config in active_configs:
            if instance_id in config.target_instances_list:

                queue_src = QueueSrc(config, instance_id)

                if queue_src.name not in self._queues_src:
                    self._queues_src[queue_src.name] = queue_src
                    logger.info(f"({queue_src.name}) Subscribed to instance {instance_id}")

                else:
                    self._queues_src[queue_src.name].stopped = False
                    logger.info(f"({queue_src.name}) Subscription already exists for instance {instance_id}")

    async def unsubscribe_from_instance(self, instance_id: str) -> None:
        self._owned_instances.discard(instance_id)

        for queue_src in self._queues_src.values():
            if queue_src.target_instance_id == instance_id:
                queue_src.stopped = True
                if queue_src.channel and not queue_src.channel.is_closed:
                    await queue_src.channel.close()
                logger.info(f"({queue_src.name}) Unsubscribed from instance {instance_id}")

    def is_mine_instance(self, instance_id: str) -> bool:
        if settings.multi_replica_mode:
            return instance_id in self._owned_instances
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Instance suspension (wifi-service integration)
    # ─────────────────────────────────────────────────────────────────────────

    async def suspend_instance(self, instance_id: str) -> None:
        for queue_src in self._queues_src.values():
            if queue_src.target_instance_id == instance_id:
                queue_src.stopped = True
                if queue_src.channel and not queue_src.channel.is_closed:
                    await queue_src.channel.close()
                logger.info(f"({queue_src.name}) Suspended instance {instance_id}")

    async def suspend_instances(self, instance_ids: list[str]) -> None:
        await asyncio.gather(
            *[
                self.suspend_instance(i)
                for i in instance_ids
            ]
        )

    def resume_instance(self, instance_id: str) -> None:
        if not self.is_mine_instance(instance_id):
            return

        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.RABBITMQ, is_active=True)

        for config in active_configs:
            if instance_id in config.target_instances_list:

                queue_src = QueueSrc(config, instance_id)

                if queue_src.name not in self._queues_src:
                    self._queues_src[queue_src.name] = queue_src
                    logger.info(f"({queue_src.name}) Resumed instance {instance_id}")

                else:
                    self._queues_src[queue_src.name].stopped = False
                    logger.info(f"({queue_src.name}) Already resumed instance {instance_id}")

    def resume_instances(self, instance_ids: list[str]) -> None:
        for i in instance_ids:
            self.resume_instance(i)

    def is_suspended_instance(self, instance_id: str) -> bool:
        return instance_id in self.config_manager.suspended_instances

    # ─────────────────────────────────────────────────────────────────────────
    # Config subscriptions
    # ─────────────────────────────────────────────────────────────────────────

    async def subscribe_to_config(self, config: AutorepubConfig) -> None:
        if not self.connection or self.connection.is_closed:
            raise RuntimeError("Cannot run subscribe_to_config: connection is unavailable")

        for target_instance_id in config.target_instances_list:
            queue_src = QueueSrc(config, target_instance_id)

            if not self.is_mine_instance(target_instance_id):
                logger.debug(
                    f"({queue_src.name}) Skipped config subscription {config.name} "
                    f"- do not own target instance {target_instance_id}"
                )
                continue

            if self.is_suspended_instance(target_instance_id):
                logger.debug(
                    f"({queue_src.name}) Skipped config subscription {config.name} "
                    f"- target instance {target_instance_id} is suspended"
                )
                continue

            if queue_src.name not in self._queues_src:
                self._queues_src[queue_src.name] = queue_src
                logger.info(f"({queue_src.name}) Subscribed to config {config.name}")

            else:
                self._queues_src[queue_src.name].stopped = False
                logger.info(f"({queue_src.name}) Subscription already exists for config {config.name}")

    async def unsubscribe_from_config(self, config: AutorepubConfig) -> None:
        for queue_src in self._queues_src.values():
            if queue_src.config.name == config.name:
                queue_src.stopped = True
                logger.info(f"({queue_src.name}) Unsubscribed from config {config.name}")

    # ─────────────────────────────────────────────────────────────────────────
    # Message callbacks
    # ─────────────────────────────────────────────────────────────────────────

    async def _handle_source_message(
        self, config: AutorepubConfig, queue_name: str, msg_id: NanoID, payload: bytes, dedup_id: str | None
    ) -> bool:
        """Handle message received from source queue."""

        if dedup_id and config.deduplication:
            dedup_id_bytes = dedup_id.encode()
            dedup_value = await self.redis.get(f"{self.DEDUP_PREFIX}:{dedup_id}")
            if dedup_value is not None:
                logger.warning(f"({queue_name}) Dedup key <{dedup_id}> already exists, skipping delivery")
                return dedup_value == b"1"
        else:
            dedup_id_bytes = b""

        queue_name_dst_bytes = self._queues_src[queue_name].name_dst.encode()
        combined_payload = PAYLOAD_SEPARATOR.join(
            (self.PAYLOAD_FORMAT_FLAG, queue_name_dst_bytes, dedup_id_bytes, payload)
        )
        delivery_params = DeliveryParams(
            receiver_id=self._queues_src[queue_name].target_instance_id,
            type=config.type,
            deduplication=config.deduplication,
            retry_max_attempts=config.retry_max_attempts,
            retry_backoff_base=config.retry_backoff_base,
            retry_multiplier=config.retry_multiplier,
            retry_max_delay=config.retry_max_delay,
        )

        await self.delivery_manager.send_message(combined_payload, delivery_params, msg_id)
        logger.info(
            f"({queue_name}) Forwarded msg [{msg_id}] <{dedup_id or 'no dedup id'}> to {delivery_params.receiver_id}"
        )
        result = await self.events_store.wait_for_result(msg_id)
        if dedup_id:
            await self.redis.set(f"{self.DEDUP_PREFIX}:{dedup_id}", int(result), ex=settings.dedup_redis_ttl)
        return result

    async def _handle_target_message(self, msg_id: NanoID, combined_payload: bytes) -> None:
        """Callback to handle target message on arrival with DeliveryManager."""

        if not self._channel_dst or self._channel_dst.pika_obj.is_closed:
            raise RuntimeError(f"[{msg_id}] Cannot run _handle_target_message: dst channel not available")

        if combined_payload[1] != ord(PAYLOAD_SEPARATOR):
            logger.debug(f"[{msg_id}] Msg is not autorepub msg, skipping")
            return

        if combined_payload[0] != ord(self.PAYLOAD_FORMAT_FLAG):
            logger.debug(f"[{msg_id}] Msg is not for this manager, skipping")
            return

        parts = combined_payload.split(PAYLOAD_SEPARATOR, TOTAL_SEPARATORS)
        if len(parts) != TOTAL_SEPARATORS + 1:
            logger.error(f"[{msg_id}] Invalid autorepub msg format, skipping")
            return

        format_flag_bytes, target_queue_name_bytes, dedup_id_bytes, original_payload = parts
        if not target_queue_name_bytes:
            logger.error(f"[{msg_id}] Target queue name is empty, skipping")
            return

        target_queue_name = target_queue_name_bytes.decode()
        # temporarily (?) disabled
        # if settings.debug_mode:
        #     target_queue_name = f"{DEBUG_PREFIX}.{target_queue_name}"

        dedup_id = dedup_id_bytes.decode()
        if dedup_id:
            dedup_exists = await self.redis.exists(f"{self.DEDUP_PREFIX}:{dedup_id}") > 0
        else:
            dedup_exists = False
            dedup_id = None

        if not dedup_exists:
            if target_queue_name not in self._queues_dst:
                self._queues_dst[target_queue_name] = await self._channel_dst.declare_pika_queue(target_queue_name)

            # FIXME: somehow detect if target queue does not exist (e.g. has been deleted since declare call)
            await self._channel_dst.publish(target_queue_name, original_payload, dedup_id)
            logger.info(f"[{msg_id}] Republished msg <{dedup_id or 'no dedup id'}> to {target_queue_name}")

            if dedup_id:
                await self.redis.set(f"{self.DEDUP_PREFIX}:{dedup_id}", b"1", ex=settings.dedup_redis_ttl)
        else:
            logger.warning(f"[{msg_id}] Dedup key <{dedup_id}> already exists, skipping republish")
