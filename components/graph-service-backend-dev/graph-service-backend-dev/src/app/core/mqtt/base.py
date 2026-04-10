"""Базовый MQTT-клиент: подключение, подписка, переподключение.
Обработка сообщений — в наследнике через handle_message(topic, payload).
"""

import logging
import time

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

DEFAULT_RECONNECT_INTERVAL = 5  # секунд
DEFAULT_CHECK_INTERVAL = 10  # секунд


class MQTTClientBase:
    """Базовый класс MQTT-клиента. Владение paho Client, подписка на топики,
    переподключение. handle_message(topic, payload) переопределяется в наследнике.
    """

    def __init__(
        self,
        host: str,
        port: int = 1883,
        keepalive: int = 60,
        username: str | None = None,
        password: str | None = None,
        topics: list[str] | None = None,
        client_id: str | None = None,
        reconnect_interval: int = DEFAULT_RECONNECT_INTERVAL,
    ):
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.username = username
        self.password = password
        self.topics = topics or []
        self.reconnect_interval = reconnect_interval

        self._client = mqtt.Client(client_id=client_id)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        if username and password:
            self._client.username_pw_set(username, password)

        self._last_reconnect_attempt: float = 0

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            for topic in self.topics:
                client.subscribe(topic)
                logger.info("Subscribed to topic: %s", topic)
            self._last_reconnect_attempt = 0
            self.on_connected(client)
        else:
            logger.error("Failed to connect to MQTT broker. Return code: %s", rc)
            if rc == 1:
                logger.error("Connection refused - incorrect protocol version")
            elif rc == 2:
                logger.error("Connection refused - invalid client identifier")
            elif rc == 3:
                logger.error("Connection refused - server unavailable")
            elif rc == 4:
                logger.error("Connection refused - bad username or password")
            elif rc == 5:
                logger.error("Connection refused - not authorised")

    def on_connected(self, client: mqtt.Client) -> None:
        """Вызывается после успешного подключения и подписки. Можно переопределить в наследнике."""
        pass

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        try:
            self.handle_message(msg.topic, msg.payload)
        except Exception as e:
            logger.exception("Error in handle_message: %s", e)

    def handle_message(self, topic: str, payload: bytes) -> None:
        """Обработка сообщения. Переопределяется в наследнике."""
        logger.debug("Message received topic=%s payload_len=%s", topic, len(payload))

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        if rc != 0:
            logger.warning("Unexpected disconnection from MQTT broker. Return code: %s", rc)
            logger.info("Will attempt to reconnect in %s seconds...", self.reconnect_interval)
            self._last_reconnect_attempt = time.time()
        else:
            logger.info("Successfully disconnected from MQTT broker")

    def start(self) -> None:
        """Подключение и запуск цикла в фоновом потоке."""
        try:
            logger.info("Connecting to MQTT broker at %s:%s", self.host, self.port)
            self._client.connect(self.host, self.port, self.keepalive)
            self._client.loop_start()
            logger.info("MQTT client started: %s:%s", self.host, self.port)
        except Exception as e:
            logger.exception("Failed to initialize MQTT client: %s", e)
            self._last_reconnect_attempt = time.time()

    def stop(self) -> None:
        """Остановка цикла и отключение."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT client stopped")

    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected())

    def check_and_reconnect(self) -> None:
        """Проверить подключение и переподключиться при необходимости."""
        if not self._client:
            return
        if self.is_connected():
            return
        now = time.time()
        if now - self._last_reconnect_attempt < self.reconnect_interval:
            return
        logger.info("Attempting to reconnect to MQTT broker...")
        self._last_reconnect_attempt = now
        try:
            self._client.reconnect()
        except Exception as e:
            logger.error("Failed to reconnect to MQTT broker: %s", e)

    def get_client(self) -> mqtt.Client:
        """Вернуть paho Client (для health-check и т.п.)."""
        return self._client
