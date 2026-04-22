"""
Конфигурация логирования с использованием Loguru.
"""
import sys
import json
from loguru import logger
from app.core.config import settings


def setup_logging():
    """
    Настройка логирования.
    """
    # Удалить стандартный handler
    logger.remove()
    
    # Добавить JSON логирование в stdout
    logger.add(
        sys.stdout,
        format="{message}",
        level=settings.LOG_LEVEL,
        serialize=True,
        colorize=False
    )

