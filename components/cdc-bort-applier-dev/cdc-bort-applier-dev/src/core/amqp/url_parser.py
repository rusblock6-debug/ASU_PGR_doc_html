"""Утилита для разбора AMQP URL на компоненты."""

from urllib.parse import urlparse


def parse_amqp_url(url: str) -> dict[str, str | int]:
    """Разобрать AMQP URL в словарь компонентов для RabbitMQClient.

    Args:
        url: AMQP URL в формате amqp://user:pass@host:port/vhost

    Returns:
        Словарь с ключами: host, port, username, password, virtual_host

    Example:
        parse_amqp_url("amqp://guest:guest@localhost:5672/")
        # {"host": "localhost", "port": 5672, "username": "guest",
        #  "password": "guest", "virtual_host": "/"}
    """
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": int(parsed.port or 5672),
        "username": parsed.username or "guest",
        "password": parsed.password or "guest",
        "virtual_host": parsed.path.lstrip("/") or "/",
    }
