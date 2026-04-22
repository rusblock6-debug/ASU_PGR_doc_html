"""Helpers for running background processes alongside the API server."""

import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from multiprocessing import Process
from typing import Final

from loguru import logger

from src.core.logger import configure_loguru

from .s3_clickhouse_etl import create_s3_clickhouse_listener

configure_loguru()

ProcessFactory = Callable[[], Process]

_REGISTERED_FACTORIES: Final[tuple[ProcessFactory, ...]] = (create_s3_clickhouse_listener,)
_WATCHDOG_INTERVAL_SECONDS: Final[float] = 5.0
_WATCHDOG_THREAD: threading.Thread | None = None
_WATCHDOG_STOP: threading.Event | None = None
_MANAGED: list["ManagedProcess"] | None = None


@dataclass
class ManagedProcess:
    name: str
    factory: ProcessFactory
    process: Process


def _start_watchdog(managed: list["ManagedProcess"]) -> None:
    global _WATCHDOG_THREAD, _WATCHDOG_STOP

    if _WATCHDOG_THREAD is not None and _WATCHDOG_THREAD.is_alive():
        return

    stop_event = threading.Event()
    _WATCHDOG_STOP = stop_event

    def _watchdog_loop() -> None:
        while not stop_event.is_set():
            for mp in managed:
                if mp.process.is_alive():
                    continue
                exitcode = mp.process.exitcode
                logger.warning(
                    "Background process {} exited (code={}); restarting",
                    mp.name,
                    exitcode,
                )
                new_process = mp.factory()
                logger.info("Starting background process {}", new_process.name)
                new_process.start()
                mp.process = new_process
            time.sleep(_WATCHDOG_INTERVAL_SECONDS)

    _WATCHDOG_THREAD = threading.Thread(
        target=_watchdog_loop,
        name="background-process-watchdog",
        daemon=True,
    )
    _WATCHDOG_THREAD.start()


def start_background_processes() -> list[Process]:
    """Instantiate and start every registered background process."""
    global _MANAGED

    processes: list[Process] = []
    managed: list[ManagedProcess] = []
    for factory in _REGISTERED_FACTORIES:
        process = factory()
        logger.info("Starting background process {}", process.name)
        process.start()
        processes.append(process)
        managed.append(ManagedProcess(name=process.name, factory=factory, process=process))
    _MANAGED = managed
    _start_watchdog(managed)
    return processes


def stop_background_processes(processes: Sequence[Process], *, timeout: float = 5.0) -> None:
    """Terminate and join previously started background processes."""
    global _WATCHDOG_THREAD, _WATCHDOG_STOP, _MANAGED

    if _WATCHDOG_STOP is not None:
        _WATCHDOG_STOP.set()
    for process in processes:
        if process.is_alive():
            logger.info("Stopping background process {}", process.name)
            process.terminate()
        process.join(timeout=timeout)
    if _WATCHDOG_THREAD is not None:
        _WATCHDOG_THREAD.join(timeout=timeout)
    _WATCHDOG_THREAD = None
    _WATCHDOG_STOP = None
    _MANAGED = None


__all__ = [
    "start_background_processes",
    "stop_background_processes",
]
