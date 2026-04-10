import asyncio
import logging
import uuid
from collections.abc import Sequence
from typing import Awaitable, Callable

import aiomqtt

from app.settings import settings

logger = logging.getLogger("mqtt_client")


class MQTTClient:
    """Async MQTT client with reconnection and pub/sub support."""

    def __init__(self, broker_host: str, broker_port: int) -> None:
        """Initialize MQTT client.

        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.instance_id = settings.instance_id
        self.client: aiomqtt.Client | None = None
        self.connected = False
        self.retry_backoff = [100, 200, 400, 800, 1600, 3200]  # ms
        self.retry_count = 0
        self.max_connection_attempts = 15
        self._monitor_connection_delay: float = 2.0
        self.subscriptions: dict[str, Callable[[str, bytes], Awaitable[None]]] = {}
        self._subscribe_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._should_reconnect = True

    async def connect(self) -> None:
        """Connect to MQTT broker with exponential backoff and max attempts."""
        # Run connection in background to allow reconnection
        while not self.connected and self.retry_count < self.max_connection_attempts:
            try:
                logger.info(
                    f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}"
                )
                self.client = aiomqtt.Client(
                    hostname=self.broker_host,
                    port=self.broker_port,
                    identifier=f"sync-{self.instance_id}-{uuid.uuid4().hex[:8]}",
                )
                # Use async context manager properly
                self.client = await self.client.__aenter__()
                self.connected = True
                self.retry_count = 0
                logger.info("Successfully connected to MQTT broker")

                # Resubscribe to topics after reconnection
                await self._resubscribe()

                # Start subscription listener
                self._subscribe_task = asyncio.create_task(self._subscription_loop())

                # Start reconnection monitor
                if not self._reconnect_task or self._reconnect_task.done():
                    self._reconnect_task = asyncio.create_task(self._monitor_connection())

                return
            except Exception as e:
                backoff_ms = self.retry_backoff[
                    min(self.retry_count, len(self.retry_backoff) - 1)
                ]
                logger.warning(
                    f"MQTT connection failed (attempt {self.retry_count + 1}): {e}. "
                    f"Retrying in {backoff_ms}ms"
                )
                self.retry_count += 1
                if self.retry_count >= self.max_connection_attempts:
                    logger.error(f"Failed to connect to MQTT broker after {self.max_connection_attempts} attempts")
                    raise RuntimeError("MQTT connection failed after max attempts")
                await asyncio.sleep(backoff_ms / 1000)

    async def _resubscribe(self) -> None:
        """Resubscribe to all topics after reconnection."""
        if not self.connected or not self.client:
            return

        for topic in list(self.subscriptions.keys()):
            try:
                await self.client.subscribe(topic, qos=0)
                logger.debug(f"Resubscribed to {topic}")
            except Exception as e:
                logger.error(f"Failed to resubscribe to {topic}: {e}")

    async def _monitor_connection(self) -> None:
        """Monitor connection health and attempt reconnection if needed."""
        try:
            while self._should_reconnect:
                await asyncio.sleep(self._monitor_connection_delay)

                if not self.connected:
                    logger.info("Connection lost, attempting to reconnect...")
                    try:
                        await self.connect()
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")
        except asyncio.CancelledError:
            logger.debug("Connection monitor cancelled")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self._should_reconnect = False  # Stop reconnection attempts

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._subscribe_task:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass

        if self.client and self.connected:
            try:
                await self.client.__aexit__(None, None, None)
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self.connected = False
                self.client = None

    async def publish(self, topic: str, payload: bytes) -> None:
        """Publish a message to a topic with auto-reconnect on failure."""
        if not self.connected or not self.client:
            logger.warning("MQTT client not connected, attempting reconnect...")
            try:
                await self.connect()
            except Exception as e:
                raise RuntimeError(f"MQTT client not connected and reconnect failed: {e}")

        try:
            await self.client.publish(  # type: ignore
                topic, payload, qos=0
            )
        except Exception as e:
            logger.error(f"Publish to {topic} failed: {e}")
            self.connected = False
            # Trigger reconnection in background
            if self._should_reconnect:
                logger.info("Triggering reconnection after publish failure")
            raise

    async def subscribe(
        self, topic: str, callback: Callable[[str, bytes], Awaitable[None]]
    ) -> None:
        """Subscribe to a topic with async callback.

        Callback receives (topic, payload) to allow extracting sender_id from topic.
        Supports MQTT wildcards: + (single level) and # (multi-level).
        """
        if not self.connected or not self.client:
            raise RuntimeError("MQTT client not connected")

        if topic in self.subscriptions:
            logger.debug(f"Subscription already exists for {topic}")
            return

        self.subscriptions[topic] = callback
        try:
            await self.client.subscribe(topic, qos=0)
            logger.debug(f"Subscribed to {topic}")
        except Exception as e:
            logger.error(f"Subscribe to {topic} failed: {e}")
            raise

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic."""
        if not self.connected or not self.client:
            return

        if topic not in self.subscriptions:
            logger.debug(f"Already unsubscribed from {topic}")
            return

        try:
            await self.client.unsubscribe(topic)
            self.subscriptions.pop(topic, None)
            logger.debug(f"Unsubscribed from {topic}")
        except Exception as e:
            logger.error(f"Unsubscribe from {topic} failed: {e}")

    async def _subscription_loop(self) -> None:
        """Listen for incoming messages and route to async callbacks."""
        if not self.client:
            logger.error("Cannot run _subscription_loop: client is unavailable")
            return

        try:
            async for message in self.client.messages:
                # Collect matching callbacks
                callbacks = [
                    callback
                    for subscribed_topic, callback in self.subscriptions.items()
                    if message.topic.matches(subscribed_topic)
                ]
                if callbacks:
                    # Executing callbacks one by one (it is faster somehow)
                    for callback in callbacks:
                        try:
                            await callback(message.topic.value, message.payload)
                        except Exception:
                            logger.exception(
                                f"Error in subscription callback {callback.__name__} for {message.topic.value}"
                            )
                    # Fire-and-forget implementation
                    # asyncio.create_task(self._execute_callbacks(callbacks, message.topic.value, message.payload))
                else:
                    logger.warning(f"No callbacks found for topic {message.topic.value}")
        except asyncio.CancelledError:
            logger.debug("Subscription loop cancelled")
            raise
        except Exception:
            logger.exception("Subscription loop error")
            self.connected = False

    async def _execute_callbacks(
        self,
        callbacks: Sequence[Callable[[str, bytes], Awaitable[None]]],
        topic: str,
        payload: bytes,
    ) -> None:
        """Safely execute a sequence of callbacks with error handling."""
        for callback in callbacks:
            try:
                await callback(topic, payload)
            except Exception:
                logger.exception(f"Error in subscription callback {callback.__name__} for {topic}")

    async def is_healthy(self) -> bool:
        """Check if client is healthy and connected."""
        return self.connected and self.client is not None
