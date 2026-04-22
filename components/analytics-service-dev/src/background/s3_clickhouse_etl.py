# ruff: noqa: D100, D103
import asyncio
from multiprocessing import Process

from src.core.faststream.application import get_app


def _worker() -> None:
    app = get_app()
    asyncio.run(app.run())


def create_s3_clickhouse_listener() -> Process:
    return Process(target=_worker, name="s3-clickhouse-etl")
