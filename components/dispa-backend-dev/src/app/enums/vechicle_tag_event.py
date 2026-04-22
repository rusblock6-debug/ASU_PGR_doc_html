"""Перечисления событий меток транспорта."""

from enum import StrEnum


class VechicleTagEventEnum(StrEnum):
    """Типы событий меток транспорта."""

    entry = "entry"
    exit = "exit"
