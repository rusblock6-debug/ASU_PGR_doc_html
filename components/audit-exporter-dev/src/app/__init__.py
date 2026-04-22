"""FastAPI application factory and lifespan wiring."""

import asyncio
import importlib.metadata
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger
from pydantic import ValidationError

from src.app.routes.health import router as health_router
from src.clickhouse.client import build_clickhouse_client
from src.core.config import AppSettings, format_settings_validation_error, get_settings
from src.core.logging import setup_logging
from src.core.orchestrator import run_polling_loop
from src.core.state import (
    BootstrapRuntimeState,
    shutdown_runtime_state,
)
from src.core.state import (
    build_runtime_state as build_bootstrap_runtime_state,
)
from src.db.source_connections import build_postgres_reader

StateLoader = Callable[[], AppSettings]


async def build_runtime_state_from_settings(
    *,
    settings_loader: StateLoader = get_settings,
) -> BootstrapRuntimeState:
    """Load settings, initialize dependency clients, and probe startup readiness."""
    try:
        settings = settings_loader()
    except ValidationError as exc:
        message = format_settings_validation_error(exc)
        raise RuntimeError(f"invalid application settings: {message}") from exc

    setup_logging(settings.log_level)

    try:
        _app_version = importlib.metadata.version("audit-exporter")
    except importlib.metadata.PackageNotFoundError:
        _app_version = "dev"
    configured_sources = [name.value for name in settings.postgres_sources()]
    logger.info(
        "app_startup",
        app_version=_app_version,
        configured_sources=configured_sources,
        poll_interval_seconds=settings.source_poll_interval_seconds,
        batch_size=settings.source_poll_batch_size,
        log_level=settings.log_level,
        dependency_connect_timeout_seconds=settings.dependency_connect_timeout_seconds,
        clickhouse_host=settings.clickhouse_host,
        clickhouse_port=settings.clickhouse_port,
        clickhouse_database=settings.clickhouse_database,
        clickhouse_secure=settings.clickhouse_secure,
    )

    postgres_readers = {
        source_name: build_postgres_reader(source_settings)
        for source_name, source_settings in settings.postgres_sources().items()
    }
    clickhouse_client = build_clickhouse_client(settings.clickhouse())

    return await build_bootstrap_runtime_state(
        settings=settings,
        postgres_readers=postgres_readers,
        clickhouse_client=clickhouse_client,
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    runtime_state = await build_runtime_state_from_settings(
        settings_loader=app.state.settings_loader,
    )
    app.state.runtime_state = runtime_state

    poll_task: asyncio.Task[None] | None = None
    try:
        if runtime_state.startup_complete and runtime_state.settings is not None:
            logger.info(
                "polling_loop_started",
                interval_seconds=runtime_state.settings.source_poll_interval_seconds,
            )
            poll_task = asyncio.create_task(
                run_polling_loop(
                    runtime_state,
                    runtime_state.settings.source_poll_interval_seconds,
                ),
            )
        yield
    finally:
        if poll_task is not None:
            poll_task.cancel()
            await asyncio.gather(poll_task, return_exceptions=True)
        await shutdown_runtime_state(runtime_state)


def create_app(*, settings_loader: StateLoader = get_settings) -> FastAPI:
    """Create the FastAPI application bound to the configured lifespan."""
    app = FastAPI(title="audit-exporter", lifespan=_lifespan)
    app.state.settings_loader = settings_loader
    app.state.runtime_state = BootstrapRuntimeState.not_started()
    app.include_router(health_router)
    return app
