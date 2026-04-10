# ruff: noqa: D100

from enum import StrEnum


class ModeType(StrEnum):
    """Место запуска проекта локальное/тестовое в докере/продакшн."""

    local = "local"
    dev = "dev"
    production = "production"
