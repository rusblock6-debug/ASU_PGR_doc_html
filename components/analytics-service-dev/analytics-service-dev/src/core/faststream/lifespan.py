# ruff: noqa: D100, D103
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from faststream import ContextRepo, FastStream

from src.api.broker import main_router
from src.core.clickhouse import pool


@asynccontextmanager
async def lifespan(context: ContextRepo) -> AsyncIterator[None]:
    app: FastStream = context.get("app")

    app.broker.include_router(main_router)  # type: ignore[union-attr]
    yield

    await pool.close_all()
