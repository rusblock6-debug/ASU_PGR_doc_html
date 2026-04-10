# ruff: noqa: D100, D101

"""Конфигурация Loguru logger."""

import json
import sys
from typing import TYPE_CHECKING, Any

from loguru import logger
from pydantic import ValidationError

if TYPE_CHECKING:
    from loguru._handler import Message


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        """Сериализация ValidationError в json."""
        if isinstance(o, ValidationError):
            return o.json()

        # Для всех остальных случаев вызываем стандартный энкодер
        return super().default(o)


def configure_loguru() -> None:
    """Настроить логирование через loguru с кастомным JSON."""
    # Убираем все дефолтные хендлеры
    logger.remove()

    # Добавляем свой JSON-сериализатор
    def json_sink(message: "Message") -> None:
        record = message.record  # type: ignore[attr-defined]
        payload = {
            "log_level": record["level"].name,
            "message": record["message"],
            "name": record["name"],
            "line": record["line"],
            "timestamp": record["time"].isoformat(),
            "extra": record.get("extra", {}),
        }
        # Пишем одну строку JSON и перевод строки
        sys.stderr.write(
            json.dumps(payload, ensure_ascii=False, cls=CustomJSONEncoder) + "\n",
        )

    logger.add(sink=json_sink, enqueue=True, catch=True, level="INFO")  # type: ignore[arg-type]
