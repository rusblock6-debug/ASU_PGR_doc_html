# ruff: noqa: D100, D101

from enum import StrEnum


class SyncStatus(StrEnum):
    CREATED = "created"
    SYNCED = "synced"
