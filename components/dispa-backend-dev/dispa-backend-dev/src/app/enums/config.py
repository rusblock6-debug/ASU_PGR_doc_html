"""Перечисления конфигурации сервиса."""

from enum import StrEnum
from typing import Self


class ServiceModeEnum(StrEnum):
    """Режимы работы сервиса."""

    bort = "bort"
    server = "server"

    @classmethod
    def modes(self) -> list[Self]:
        """Получить список доступных режимов."""
        return [self.bort, self.server]
