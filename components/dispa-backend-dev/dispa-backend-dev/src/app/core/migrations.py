"""Инициализация БД для trip-service.

Автоматическое применение Alembic миграций при старте сервиса.
"""

import asyncio
import os
import subprocess
from pathlib import Path

from loguru import logger


async def run_migrations() -> None:
    """Запуск Alembic миграций перед стартом сервиса (аналогично graph-service-backend)."""
    try:
        logger.info("Running database migrations...")

        # Ищем директорию с alembic.ini вверх по дереву
        app_dir = Path(__file__).parent.parent.parent
        while not (app_dir / "alembic.ini").exists() and app_dir != app_dir.parent:
            app_dir = app_dir.parent

        env = os.environ.copy()
        env.setdefault("PYTHONPATH", "/app")

        # Простой запуск alembic через subprocess (как в graph-service-backend)
        cmd = ["alembic", "upgrade", "head"]

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(  # noqa: S603
                cmd,
                cwd=str(app_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,  # Не выбрасываем исключение, проверяем returncode
            ),
        )

        if result.returncode == 0:
            if result.stdout:
                logger.debug("Migration output", output=result.stdout)
            logger.info("Database migrations completed successfully")
        else:
            error_msg = f"Alembic migration failed: {result.stderr or result.stdout}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    except subprocess.TimeoutExpired as e:
        error_msg = "Alembic migration timeout (60s)"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e
    except RuntimeError:
        raise
    except Exception as e:
        error_msg = f"Failed to run migrations: {e}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e
