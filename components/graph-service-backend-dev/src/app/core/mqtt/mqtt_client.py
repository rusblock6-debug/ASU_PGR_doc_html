"""Точка входа MQTT для graph-service: инициализация, checker, API для main/health.
Класс GraphVehicleMQTTClient и логика телеметрии — в mqtt_graph_vehicles.
"""

import logging
import threading
import time

import paho.mqtt.client as mqtt

from app.core.mqtt.mqtt_graph_vehicles import GraphVehicleMQTTClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHECK_INTERVAL = 10  # секунд


def init_mqtt_client() -> None:
    """Инициализация и запуск MQTT-клиента (совместимость с main.py)."""
    GraphVehicleMQTTClient.get_or_create().start()


def get_mqtt_client() -> mqtt.Client | None:
    """Вернуть paho Client для health-check и т.п."""
    client = GraphVehicleMQTTClient.get_instance()
    return client.get_client() if client else None


def start_connection_checker() -> None:
    """Запуск фонового потока проверки подключения и переподключения MQTT."""

    def _checker() -> None:
        while True:
            time.sleep(CHECK_INTERVAL)
            instance = GraphVehicleMQTTClient.get_instance()
            if instance is not None:
                instance.check_and_reconnect()

    thread = threading.Thread(target=_checker, daemon=True)
    thread.start()
    logger.info("MQTT connection checker started")


def stop_mqtt_client() -> None:
    """Остановка MQTT-клиента."""
    GraphVehicleMQTTClient.reset_instance()
