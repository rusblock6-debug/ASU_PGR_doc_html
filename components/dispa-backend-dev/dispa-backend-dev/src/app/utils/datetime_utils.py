"""Datetime utilities for the trip service."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def format_datetime_for_message(dt: datetime | None) -> str:
    """Форматирует datetime для отображения в сообщениях пользователю.

    Формат: DD.MM.YYYY HH:MM в таймзоне приложения.
    Если dt=None, возвращает "не завершён".
    """
    if not dt:
        return "не завершён"

    try:
        tz = ZoneInfo(settings.timezone)
        if dt.tzinfo is None:
            # Если datetime наивный, считаем что это UTC
            dt = dt.replace(tzinfo=UTC)
        dt_local = dt.astimezone(tz)
        return dt_local.strftime("%d.%m.%Y %H:%M")
    except Exception:
        # Fallback на исходный формат если что-то пошло не так
        return dt.strftime("%d.%m.%Y %H:%M")


def format_time_for_message(dt: datetime | None) -> str:
    """Форматирует datetime для отображения времени в сообщениях пользователю.

    Формат: HH:MM:SS в таймзоне приложения.
    Если dt=None, возвращает пустую строку.
    """
    if not dt:
        return ""

    try:
        tz = ZoneInfo(settings.timezone)
        if dt.tzinfo is None:
            # Если datetime наивный, считаем что это UTC
            dt = dt.replace(tzinfo=UTC)
        dt_local = dt.astimezone(tz)
        return dt_local.strftime("%H:%M:%S")
    except Exception:
        # Fallback на исходный формат если что-то пошло не так
        return dt.strftime("%H:%M:%S")


def truncate_datetime_to_seconds(dt: datetime, as_iso_z: bool = False) -> datetime | str:
    """Отбрасывает микросекунды из datetime.

    Args:
        dt: Исходный datetime объект
        as_iso_z: Если True, вернуть строку формата 2026-02-02T15:16:58Z (UTC)

    Returns:
        datetime без микросекунд, либо строка ISO с Z при as_iso_z=True
    """
    truncated = dt.replace(microsecond=0)
    if as_iso_z:
        if truncated.tzinfo is None:
            truncated = truncated.replace(tzinfo=UTC)
        truncated = truncated.astimezone(UTC)
        return truncated.strftime("%Y-%m-%dT%H:%M:%SZ")
    return truncated
