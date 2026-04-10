# ruff: noqa: D100, D103
from faststream.rabbit import RabbitBroker, RabbitRouter


def init_main_router(broker: RabbitBroker, router: RabbitRouter) -> None:
    broker.include_router(router)
