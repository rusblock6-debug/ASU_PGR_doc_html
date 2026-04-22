# ruff: noqa: D100, D101

from enum import StrEnum


class LogSeverity(StrEnum):
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    debug = "DEBUG"
    critical = "CRITICAL"
