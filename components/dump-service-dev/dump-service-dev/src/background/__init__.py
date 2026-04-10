"""Helpers for running background processes alongside the API server."""

from collections.abc import Callable, Sequence
from multiprocessing import Process
from typing import Final

from loguru import logger

from .ekiper_listener import create_ekiper_listener
from .trip_service_listener import create_trip_service_listener
from .wifi_listener import create_wifi_listener

ProcessFactory = Callable[[], Process]

_REGISTERED_FACTORIES: Final[tuple[ProcessFactory, ...]] = (
    create_trip_service_listener,
    create_wifi_listener,
    create_ekiper_listener,
)


def start_background_processes() -> list[Process]:
    """Instantiate and start every registered background process."""
    processes: list[Process] = []
    for factory in _REGISTERED_FACTORIES:
        process = factory()
        logger.info("Starting background process {}", process.name)
        process.start()
        processes.append(process)
    return processes


def stop_background_processes(processes: Sequence[Process], *, timeout: float = 5.0) -> None:
    """Terminate and join previously started background processes."""
    for process in processes:
        if process.is_alive():
            logger.info("Stopping background process {}", process.name)
            process.terminate()
        process.join(timeout=timeout)


__all__ = [
    "start_background_processes",
    "stop_background_processes",
]
