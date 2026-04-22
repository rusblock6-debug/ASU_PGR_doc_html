import asyncio
import logging

from aiomqtt import Topic

from app.delivery.delivery_manager import DeliveryManager
from app.models.schemas import AutorepubConfig, DeliveryParams
from app.models.types import AutorepubConfigType, NanoID
from app.mqtt.client import MQTTClient
from app.settings import settings

from .config_manager import AutorepubConfigManager
from .consts import PAYLOAD_SEPARATOR, TOTAL_SEPARATORS  # DEBUG_PREFIX

logger = logging.getLogger("autorepub.mqtt")


class AutorepubMQTTManager:
    """Manages autorepub message transfer between MQTT topics on different instances."""

    PAYLOAD_FORMAT_FLAG = b"m"

    def __init__(
        self,
        config_manager: AutorepubConfigManager,
        delivery_manager: DeliveryManager,
        mqtt_client: MQTTClient,
    ) -> None:
        """Initialize autorepub manager."""

        self.config_manager = config_manager
        self.delivery_manager = delivery_manager
        self.mqtt_client = mqtt_client

        self._owned_instances: set[str] = set()

    async def start(self) -> None:
        """Start autorepub manager and subscribe to active configs."""

        # Subscribe to all active configs
        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.MQTT, is_active=True)
        for config in active_configs:
            await self.subscribe_to_config(config)

        logger.info("Autorepub manager started")

    async def stop(self) -> None:
        """Stop autorepub manager and cleanup."""
        logger.info("Autorepub manager stopped")

    # ─────────────────────────────────────────────────────────────────────────
    # Instance ownership (multi_replica_mode)
    # ─────────────────────────────────────────────────────────────────────────

    async def subscribe_to_instance(self, instance_id: str) -> None:
        self._owned_instances.add(instance_id)

        if self.is_suspended_instance(instance_id):
            return

        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.MQTT, is_active=True)
        for config in active_configs:
            if instance_id in config.target_instances_list:
                await self.subscribe_to_config(config)

    async def unsubscribe_from_instance(self, instance_id: str) -> None:
        self._owned_instances.discard(instance_id)
        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.MQTT, is_active=True)
        for config in active_configs:
            if (
                instance_id in config.target_instances_list
                and not any(self.is_mine_instance(i_id) for i_id in config.target_instances_list)
            ):
                await self.unsubscribe_from_config(config)

    def is_mine_instance(self, instance_id: str) -> bool:
        if settings.multi_replica_mode:
            return instance_id in self._owned_instances
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Instance suspension (wifi-service integration)
    # ─────────────────────────────────────────────────────────────────────────

    async def suspend_instance(self, instance_id: str) -> None:
        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.MQTT, is_active=True)
        for config in active_configs:
            if instance_id in config.target_instances_list:
                await self.unsubscribe_from_config(config)

    async def suspend_instances(self, instance_ids: list[str]) -> None:
        await asyncio.gather(
            *[
                self.suspend_instance(i)
                for i in instance_ids
            ]
        )

    async def resume_instance(self, instance_id: str) -> None:
        active_configs = self.config_manager.get_configs(type_=AutorepubConfigType.MQTT, is_active=True)
        for config in active_configs:
            if (
                instance_id in config.target_instances_list
                and any(self.is_mine_instance(i_id) for i_id in config.target_instances_list)
                and not any(self.is_suspended_instance(i_id) for i_id in config.target_instances_list)
            ):
                await self.subscribe_to_config(config)

    async def resume_instances(self, instance_ids: list[str]) -> None:
        await asyncio.gather(
            *[
                self.resume_instance(i)
                for i in instance_ids
            ]
        )

    def is_suspended_instance(self, instance_id: str) -> bool:
        return instance_id in self.config_manager.suspended_instances

    # ─────────────────────────────────────────────────────────────────────────
    # Config subscriptions
    # ─────────────────────────────────────────────────────────────────────────

    async def subscribe_to_config(self, config: AutorepubConfig) -> None:
        """Subscribe to a config's MQTT topic."""

        if not any(self.is_mine_instance(i) for i in config.target_instances_list):
            logger.debug(
                f"({config.source_topic}) Skipped config subscription {config.name} "
                f"- do not own any of target instances"
            )
            return
        if any(self.is_suspended_instance(i) for i in config.target_instances_list):
            logger.debug(
                f"({config.source_topic}) Skipped config subscription {config.name} "
                f"- some of target instances are suspended"
            )
            return
        try:
            await self.mqtt_client.subscribe(config.source_topic, self._handle_source_message)
            logger.info(f"({config.source_topic}) Subscribed to config {config.name}")
        except Exception:
            logger.exception(f"({config.source_topic}) Failed to subscribe to config {config.name}")

    async def unsubscribe_from_config(self, config: AutorepubConfig) -> None:
        """Unsubscribe from a config's MQTT topic."""
        try:
            await self.mqtt_client.unsubscribe(config.source_topic)
            logger.info(f"({config.source_topic}) Unsubscribed from config {config.name}")
        except Exception:
            logger.exception(f"({config.source_topic}) Failed to unsubscribe from config {config.name}")

    # ─────────────────────────────────────────────────────────────────────────
    # Message callbacks
    # ─────────────────────────────────────────────────────────────────────────

    async def _handle_source_message(self, topic: str, payload: bytes) -> None:
        """Handle message received from source topic."""

        # Find active config for this topic
        config = None
        topic_obj = Topic(topic)
        for _config in self.config_manager.get_configs(AutorepubConfigType.MQTT, is_active=True):
            if topic_obj.matches(_config.source_topic):
                config = _config
                break
        if not config:
            logger.warning(f"({topic}) Skipped msg - no active config found")
            return

        # Combine target_topic with message content
        target_topic = config.get_target_topic()
        if "+" in target_topic or "#" in target_topic:
            target_topic = topic
        target_topic_bytes = target_topic.encode()
        combined_payload = PAYLOAD_SEPARATOR.join(
            (self.PAYLOAD_FORMAT_FLAG, target_topic_bytes, b"", payload)
        )

        for target_instance_id in config.target_instances_list:
            if not self.is_mine_instance(target_instance_id):
                logger.debug(f"({topic}) Skipped msg - do not own instance {target_instance_id}")
                continue
            delivery_params = DeliveryParams(
                receiver_id=target_instance_id,
                type=config.type,
                deduplication=config.deduplication,
                retry_max_attempts=config.retry_max_attempts,
                retry_backoff_base=config.retry_backoff_base,
                retry_multiplier=config.retry_multiplier,
                retry_max_delay=config.retry_max_delay,
            )
            # Store and send via DeliveryManager
            msg_id = await self.delivery_manager.send_message(combined_payload, delivery_params)
            logger.info(f"({topic}) Forwarded msg [{msg_id}] to {target_instance_id}")

    async def _handle_target_message(self, msg_id: NanoID, combined_payload: bytes) -> None:
        """Callback to handle target message on arrival with DeliveryManager."""

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

        format_flag_bytes, target_topic_bytes, empty_bytes, original_payload = parts
        if not target_topic_bytes:
            logger.debug(f"[{msg_id}] Target topic is empty, skipping")
            return

        target_topic = target_topic_bytes.decode()
        # temporarily (?) disabled
        # if settings.debug_mode:
        #     target_topic = f"{DEBUG_PREFIX}/{target_topic}"

        await self.mqtt_client.publish(target_topic, original_payload)
        logger.info(f"[{msg_id}] Republished msg to {target_topic}")
