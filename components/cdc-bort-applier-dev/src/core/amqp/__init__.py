"""AMQP infrastructure package."""

from src.core.amqp.consumer import AmqpConsumer
from src.core.amqp.url_parser import parse_amqp_url

__all__ = ["AmqpConsumer", "parse_amqp_url"]
