"""Модуль кастомных exception для слоя приложения."""

from .dump import DumpCanNotBeEmpty, DumpIsAlreadyGenerated

__all__ = ["DumpCanNotBeEmpty", "DumpIsAlreadyGenerated"]
