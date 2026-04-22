"""Менеджер для запуска и управления несколькими StreamApp с retry."""

import asyncio
import random
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from .app import StreamApp
from .router import StreamRouter

Lifespan = Callable[[], AbstractAsyncContextManager[Any]]


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 5
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class StreamAppConfig:
    """Configuration for a single StreamApp instance."""

    name: str
    router: StreamRouter
    host: str
    port: int
    vhost: str
    username: str
    password: str
    lifespan: Any  # Required: lifespan function for this app (e.g. make_bort_lifespan(...))


@dataclass
class StreamAppManager:
    """Manages multiple StreamApp instances with isolated databases."""

    configs: list[StreamAppConfig]
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    _apps: dict[str, StreamApp] = field(default_factory=dict, init=False)
    _started: bool = field(default=False, init=False)

    async def start(self) -> None:
        """Start all StreamApps with isolated databases."""
        if self._started:
            logger.warning("StreamAppManager already started")
            return

        logger.info(f"Starting StreamAppManager with {len(self.configs)} apps")

        # Start all apps with retry (each will create its own pool)
        start_tasks = [self._start_app_with_retry(config) for config in self.configs]

        try:
            await asyncio.gather(*start_tasks)
            self._started = True
            logger.info("All StreamApps started successfully")
        except Exception as e:
            logger.error(f"Failed to start StreamApps: {e}")
            await self.stop()
            raise

    async def _start_app_with_retry(self, config: StreamAppConfig) -> None:
        """Start a single StreamApp with isolated database."""
        retry_count = 0
        delay = self.retry_config.initial_delay

        app_lifespan = config.lifespan
        logger.debug(f"Using lifespan for app={config.name}")

        # Create StreamApp with isolated lifespan
        app = StreamApp(
            router=config.router,
            name=config.name,
            lifespan=app_lifespan,
            host=config.host,
            port=config.port,
            vhost=config.vhost,
            username=config.username,
            password=config.password,
        )

        while retry_count < self.retry_config.max_retries:
            try:
                logger.info(
                    f"Starting StreamApp name={config.name} "
                    f"(attempt {retry_count + 1}/{self.retry_config.max_retries})",
                )
                await app.start()

                self._apps[config.name] = app
                logger.info(f"StreamApp name={config.name} started successfully")
                return
            except Exception as e:
                retry_count += 1
                if retry_count >= self.retry_config.max_retries:
                    logger.error(
                        f"Failed to start StreamApp name={config.name} "
                        f"after {self.retry_config.max_retries} attempts: {e}",
                    )
                    raise RuntimeError(
                        f"Failed to start StreamApp name={config.name} "
                        f"after {self.retry_config.max_retries} attempts",
                    ) from e

                # Calculate sleep time with exponential backoff
                sleep_time = min(delay, self.retry_config.max_delay)

                # Add jitter if enabled
                if self.retry_config.jitter:
                    jitter_amount = sleep_time * 0.1  # 10% jitter
                    sleep_time += random.uniform(-jitter_amount, jitter_amount)  # noqa: S311

                logger.warning(
                    f"Failed to start StreamApp name={config.name}: {e}. "
                    f"Retrying in {sleep_time:.2f}s "
                    f"(attempt {retry_count}/{self.retry_config.max_retries})",
                )

                await asyncio.sleep(sleep_time)
                delay *= self.retry_config.exponential_base

    async def run(self) -> None:
        """Run all StreamApps in parallel."""
        if not self._started:
            raise RuntimeError("StreamAppManager not started. Call start() first.")

        logger.info(f"Running {len(self._apps)} StreamApps")

        # Run all apps in parallel
        run_tasks = [
            self._run_app_with_error_handling(name, app) for name, app in self._apps.items()
        ]

        try:
            await asyncio.gather(*run_tasks)
        except Exception as e:
            logger.error(f"Error running StreamApps: {e}")
            raise

    async def _run_app_with_error_handling(
        self,
        name: str,
        app: StreamApp,
    ) -> None:
        """Run a single StreamApp with error handling."""
        try:
            logger.debug(f"StreamApp name={name} entering run loop")
            await app.run()
        except Exception as e:
            logger.error(f"StreamApp name={name} crashed: {e}")
            raise

    async def stop(self) -> None:
        """Gracefully stop all StreamApps."""
        if not self._apps:
            logger.info("No StreamApps to stop")
            return

        logger.info(f"Stopping {len(self._apps)} StreamApps")

        # Stop all apps (each will cleanup its own pool via lifespan)
        stop_tasks = [
            self._stop_app_with_timeout(name, app, timeout=30.0) for name, app in self._apps.items()
        ]

        results = await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Log errors
        for name, result in zip(self._apps.keys(), results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Error stopping StreamApp name={name}: {result}")

        self._apps.clear()
        self._started = False
        logger.info("All StreamApps stopped")

    async def _stop_app_with_timeout(
        self,
        name: str,
        app: StreamApp,
        timeout: float,
    ) -> None:
        """Stop a single StreamApp with timeout."""
        try:
            logger.debug(f"Stopping StreamApp name={name}")
            await asyncio.wait_for(app.stop(), timeout=timeout)
            logger.info(f"StreamApp name={name} stopped successfully")
        except TimeoutError:
            logger.error(
                f"Timeout stopping StreamApp name={name} after {timeout}s",
            )
            raise
        except Exception as e:
            logger.error(f"Error stopping StreamApp name={name}: {e}")
            raise
