"""Запуск outbox-демона, который публикует аудит-записи в RabbitMQ Stream.

Запуск:
    python -m examples.run_daemon

Необходимые зависимости:
    uv add "audit-lib[daemon]"

Демон работает как отдельный процесс рядом с FastAPI-приложением.
Остановка — Ctrl+C или SIGTERM (graceful shutdown).
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from audit_lib import configure_audit
from audit_lib.daemon import OutboxDaemon

# Используйте тот же Base, что и в FastAPI-приложении,
# или создайте AuditOutbox заново — главное, чтобы таблица совпадала.
from examples.fastapi_app import AuditOutbox, DATABASE_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine)

    daemon = OutboxDaemon(
        session_factory=session_factory,
        outbox_model=AuditOutbox,
        # RabbitMQ Stream
        host="localhost",
        port=5552,
        username="guest",
        password="guest",
        stream_name="audit-events",
        # Polling
        batch_size=100,
        poll_interval=1.0,
        # Retry
        max_backoff=60.0,
        # Cleanup — удалять обработанные записи старше 72ч
        retention_hours=72,
        cleanup_interval_hours=1.0,
    )

    await daemon.run()  # блокирует до SIGINT/SIGTERM


if __name__ == "__main__":
    asyncio.run(main())
