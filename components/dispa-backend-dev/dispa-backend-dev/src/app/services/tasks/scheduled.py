"""Периодические (scheduled) задачи для server mode.

Этот модуль содержит фоновые задачи, которые запускаются
только в серверном режиме (settings.service_mode == "server").
"""

import asyncio
from typing import Any

from loguru import logger

from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.services import ShiftTaskService
from app.services.full_shift_state_service import full_shift_state_service

# Интервал выполнения задачи расчета статусов смен (секунды)
FULL_SHIFT_STATE_INTERVAL_SECONDS = 60

# Глобальная ссылка на задачу для управления жизненным циклом
_full_shift_state_task: asyncio.Task[None] | None = None


async def _run_full_shift_state_calculation() -> None:
    """Фоновая задача для периодической обработки смен в server mode.

    Раз в `FULL_SHIFT_STATE_INTERVAL_SECONDS` секунд:
    - пересчитывает обобщенные статусы смен через `full_shift_state_service`
    - при включенном `settings.shift_auto_switch` отслеживает смену текущих
      режимов работы и копирует задания из предыдущей смены в новую

    На первом проходе после старта только инициализирует кеш текущих смен
    без копирования заданий.
    """
    logger.info(
        "Starting full_shift_state calculation background task",
        interval_seconds=FULL_SHIFT_STATE_INTERVAL_SECONDS,
    )

    # Даем время на запуск сервиса перед первым выполнением
    await asyncio.sleep(10)
    current_shift_data: dict[int, dict[str, Any]] = {}

    while True:
        try:
            logger.debug("Running full_shift_state calculation...")
            stats = await full_shift_state_service.process_all_shifts()
            if settings.shift_auto_switch:
                async with AsyncSessionLocal() as session:
                    current_shift_data = await ShiftTaskService(session).copy_from_previous_shift(
                        current_shift_data,
                    )
            logger.info(
                "Full shift state calculation completed",
                **stats,
            )
        except asyncio.CancelledError:
            logger.info("Full shift state calculation task cancelled")
            break
        except Exception as e:
            logger.error(
                "Error in full_shift_state calculation",
                error=str(e),
                exc_info=True,
            )

        # Ждем до следующего выполнения
        await asyncio.sleep(FULL_SHIFT_STATE_INTERVAL_SECONDS)


async def start_scheduled_tasks() -> None:
    """Запустить все периодические задачи для server mode.

    Вызывается из lifespan при старте приложения.
    Задачи запускаются только если settings.service_mode == "server".
    """
    global _full_shift_state_task

    if settings.service_mode != "server":
        return

    logger.info("Starting scheduled tasks for server mode")

    # Запускаем задачу расчета обобщенных статусов смен
    _full_shift_state_task = asyncio.create_task(
        _run_full_shift_state_calculation(),
        name="full_shift_state_calculation",
    )

    logger.info("Scheduled tasks started successfully")


async def stop_scheduled_tasks() -> None:
    """Остановить все периодические задачи.

    Вызывается из lifespan при остановке приложения.
    """
    global _full_shift_state_task

    if _full_shift_state_task is not None:
        logger.info("Stopping full_shift_state calculation task...")
        _full_shift_state_task.cancel()
        try:
            await _full_shift_state_task
        except asyncio.CancelledError:
            pass
        _full_shift_state_task = None
        logger.info("Full shift state calculation task stopped")

    logger.info("All scheduled tasks stopped")
