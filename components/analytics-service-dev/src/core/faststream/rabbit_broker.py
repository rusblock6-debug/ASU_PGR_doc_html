"""RabbitBroker."""

import logging

from faststream.rabbit import RabbitBroker
from faststream.rabbit.utils import RabbitClientProperties
from loguru import logger

from src.core.config import get_settings

settings = get_settings()


broker = RabbitBroker(
    settings.RABBIT_URL,
    fail_fast=False,
    logger=logger,
    log_level=logging.DEBUG,
    reconnect_interval=5.0,
    client_properties=RabbitClientProperties(
        heartbeat=30,
    ),
)
