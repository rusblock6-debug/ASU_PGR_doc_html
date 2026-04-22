# ruff: noqa: E402
#!/usr/bin/env python3
"""CLI скрипт для мониторинга CDC событий из RabbitMQ Streams."""

import argparse
import asyncio
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Добавить корень проекта в sys.path для импорта src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import msgspec
from loguru import logger
from rstream import Consumer, ConsumerOffsetSpecification, MessageContext, OffsetType

from src.app.model.cdc_event import Envelope
from src.app.utils.table_extractor import extract_table_name
from src.app.utils.type_converter import TypeConverter
from src.core.logging import LogConfig, LogFormat, setup_logging


class EchoHandler:
    """Обработчик для вывода CDC событий."""

    def __init__(
        self,
        *,
        pretty: bool = True,
        show_schema: bool = False,
        filter_table: str | None = None,
        no_color: bool = False,
    ) -> None:
        self.pretty = pretty
        self.show_schema = show_schema
        self.filter_table = filter_table
        self.no_color = no_color
        self.type_converter = TypeConverter()
        self.event_count = 0

    def handle(self, envelope: Envelope, offset: int) -> None:
        """
        Обрабатывает и выводит одно CDC событие.

        Args:
            envelope: Декодированное CDC событие
            offset: Offset события в стриме
        """
        # Извлечь имя таблицы
        try:
            table_name = extract_table_name(envelope.schema.name)
        except Exception:
            table_name = "unknown"

        # Фильтрация по таблице
        if self.filter_table and table_name != self.filter_table:
            return

        # Конвертировать payload через TypeConverter
        field_types = {f.field: f.name for f in envelope.schema.fields}
        converted_payload = {
            key: self.type_converter.convert_value(value, field_types.get(key, ""), key)
            for key, value in envelope.payload.items()
        }

        # Форматировать datetime объекты в JSON-совместимые строки
        json_compatible_payload = self._make_json_compatible(converted_payload)

        # Вывести заголовок
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"[{timestamp}] offset={offset} table={table_name}"

        if not self.no_color:
            # Цветной вывод (синий для заголовка)
            print(f"\033[34m{header}\033[0m")
        else:
            print(header)

        # Вывести payload
        if self.pretty:
            payload_json = json.dumps(
                json_compatible_payload,
                indent=2,
                ensure_ascii=False,
            )
        else:
            payload_json = json.dumps(json_compatible_payload, ensure_ascii=False)

        print(payload_json)

        # Вывести schema если требуется
        if self.show_schema:
            schema_data = {
                "type": envelope.schema.type,
                "name": envelope.schema.name,
                "optional": envelope.schema.optional,
                "fields": [
                    {
                        "field": f.field,
                        "type": f.type,
                        "optional": f.optional,
                        "name": f.name,
                    }
                    for f in envelope.schema.fields
                ],
            }
            if self.pretty:
                schema_json = json.dumps(schema_data, indent=2, ensure_ascii=False)
            else:
                schema_json = json.dumps(schema_data, ensure_ascii=False)

            if not self.no_color:
                print("\033[33mSchema:\033[0m")
            else:
                print("Schema:")
            print(schema_json)

        print()  # Пустая строка между событиями
        self.event_count += 1

    def _make_json_compatible(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Преобразует datetime объекты в строки для JSON serialization.

        Args:
            data: Данные с возможными datetime объектами

        Returns:
            JSON-совместимый словарь
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = self._make_json_compatible(value)
            elif isinstance(value, list):
                result[key] = [
                    self._make_json_compatible(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def print_statistics(self) -> None:
        """Выводит статистику обработанных событий."""
        msg = f"Total events processed: {self.event_count}"
        if not self.no_color:
            print(f"\033[32m{msg}\033[0m")
        else:
            print(msg)


class EchoConsumer:
    """Упрощенный consumer для echo."""

    def __init__(
        self,
        *,
        stream: str,
        host: str,
        port: int,
        vhost: str,
        username: str,
        password: str,
        offset_spec: ConsumerOffsetSpecification,
        handler: EchoHandler,
    ) -> None:
        self.stream = stream
        self.host = host
        self.port = port
        self.vhost = vhost
        self.username = username
        self.password = password
        self.offset_spec = offset_spec
        self.handler = handler
        self.consumer: Consumer | None = None
        self.decoder = msgspec.json.Decoder(Envelope)

    async def start(self) -> None:
        """Запускает consumer и подписывается на stream."""
        logger.info(
            "Starting echo consumer stream={stream} host={host} port={port}",
            stream=self.stream,
            host=self.host,
            port=self.port,
        )

        self.consumer = Consumer(
            host=self.host,
            port=self.port,
            vhost=self.vhost,
            username=self.username,
            password=self.password,
            load_balancer_mode=True,
        )

        try:
            await self.consumer.start()
            logger.info("Consumer started")

            await self.consumer.subscribe(
                stream=self.stream,
                callback=self._on_message,
                offset_specification=self.offset_spec,
                subscriber_name=f"echo-{self.stream}",
            )
            logger.info("Subscribed to stream={stream}", stream=self.stream)
        except Exception as e:
            logger.error("Failed to start consumer: {error}", error=str(e))
            raise

    async def run(self) -> None:
        """Запускает основной цикл обработки."""
        if self.consumer is None:
            raise RuntimeError("Consumer not started. Call start() first.")
        await self.consumer.run()

    async def stop(self) -> None:
        """Останавливает consumer."""
        logger.info("Stopping echo consumer")
        if self.consumer:
            await self.consumer.close()
            self.consumer = None
        logger.info("Consumer stopped")

    async def _on_message(self, body: bytes, ctx: MessageContext) -> None:
        """
        Callback для обработки сообщения из stream.

        Args:
            body: Тело сообщения (bytes)
            ctx: Контекст сообщения с offset
        """
        try:
            # Конвертировать memoryview в bytes если нужно
            if isinstance(body, memoryview):
                body = bytes(body)

            # Удалить AMQP header
            body = self._strip_amqp_header(body)

            # Декодировать событие
            envelope = self.decoder.decode(body)

            # Передать в handler
            self.handler.handle(envelope, ctx.offset)
        except msgspec.DecodeError as e:
            logger.error(
                "Failed to decode message offset={offset}: {error}",
                offset=ctx.offset,
                error=str(e),
            )
            # Показать первые 500 байт для отладки
            preview = body[:500].decode("utf-8", errors="replace")
            logger.debug("Message preview: {preview}", preview=preview)
        except Exception as e:
            logger.exception(
                "Error processing message offset={offset}: {error}",
                offset=ctx.offset,
                error=str(e),
            )

    @staticmethod
    def _strip_amqp_header(body: bytes) -> bytes:
        """Удаляет AMQP 1.0 header из сообщения."""
        if body.startswith(b"\x00Su\xb0"):
            return body[8:]
        if not body.startswith(b"{"):
            idx = body.find(b"{")
            if idx != -1:
                return body[idx:]
        return body


class GracefulShutdown:
    """Менеджер для graceful shutdown."""

    def __init__(self) -> None:
        self.shutdown_event: asyncio.Event | None = None
        self.loop: asyncio.AbstractEventLoop | None = None

    def setup(self, loop: asyncio.AbstractEventLoop) -> None:
        """Устанавливает signal handlers."""
        self.loop = loop
        self.shutdown_event = asyncio.Event()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._signal_handler, sig)
        logger.debug("Signal handlers installed")

    def _signal_handler(self, signum: int) -> None:
        """Обработчик сигналов."""
        logger.info("Received signal={signal}, shutting down...", signal=signum)
        if self.shutdown_event:
            self.shutdown_event.set()

    async def wait(self) -> None:
        """Ожидает сигнал shutdown."""
        if self.shutdown_event:
            await self.shutdown_event.wait()

    def restore(self) -> None:
        """Восстанавливает оригинальные signal handlers."""
        if self.loop:
            for sig in (signal.SIGTERM, signal.SIGINT):
                self.loop.remove_signal_handler(sig)


def parse_args() -> argparse.Namespace:
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="CLI tool for monitoring CDC events from RabbitMQ Streams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python scripts/echo.py --stream cdc-graph-service

  # Filter by table
  python scripts/echo.py --stream cdc-graph-service --filter-table users

  # Compact JSON output
  python scripts/echo.py --stream cdc-graph-service --compact

  # Show schema
  python scripts/echo.py --stream cdc-graph-service --show-schema

  # Start from specific offset
  python scripts/echo.py --stream cdc-graph-service --offset 1000

  # Start from last offset
  python scripts/echo.py --stream cdc-graph-service --offset-last

  # Custom connection parameters
  python scripts/echo.py \\
    --stream cdc-graph-service \\
    --host rabbitmq.example.com \\
    --port 5552 \\
    --user admin \\
    --password secret

  # No colors (for piping to file)
  python scripts/echo.py --stream cdc-graph-service --no-color > events.log
        """,
    )

    # Обязательные аргументы
    parser.add_argument(
        "--stream",
        required=True,
        help="Stream name to subscribe to",
    )

    # Подключение к RabbitMQ
    rabbit_group = parser.add_argument_group("RabbitMQ connection")
    rabbit_group.add_argument(
        "--host",
        default=os.getenv("RABBIT_HOST", "localhost"),
        help="RabbitMQ host (default: from .env or localhost)",
    )
    rabbit_group.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("RABBIT_PORT", "5552")),
        help="RabbitMQ port (default: from .env or 5552)",
    )
    rabbit_group.add_argument(
        "--user",
        default=os.getenv("RABBIT_USER", "guest"),
        help="RabbitMQ username (default: from .env or guest)",
    )
    rabbit_group.add_argument(
        "--password",
        default=os.getenv("RABBIT_PASSWORD", "guest"),
        help="RabbitMQ password (default: from .env or guest)",
    )
    rabbit_group.add_argument(
        "--vhost",
        default=os.getenv("RABBIT_VHOST", "/"),
        help="RabbitMQ vhost (default: from .env or /)",
    )

    # Форматирование вывода
    output_group = parser.add_argument_group("Output formatting")
    output_group.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty print JSON (default: True)",
    )
    output_group.add_argument(
        "--compact",
        action="store_true",
        help="Compact JSON output (overrides --pretty)",
    )
    output_group.add_argument(
        "--show-schema",
        action="store_true",
        help="Show schema along with payload",
    )
    output_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    # Фильтрация
    filter_group = parser.add_argument_group("Filtering")
    filter_group.add_argument(
        "--filter-table",
        help="Filter by table name",
    )

    # Offset управление
    offset_group = parser.add_argument_group("Offset management")
    offset_group.add_argument(
        "--offset",
        type=int,
        help="Start from specific offset",
    )
    offset_group.add_argument(
        "--offset-last",
        action="store_true",
        help="Start from last offset",
    )

    # Логирование
    log_group = parser.add_argument_group("Logging")
    log_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Log level (default: WARNING)",
    )

    args = parser.parse_args()

    # Обработка --compact override
    if args.compact:
        args.pretty = False

    return args


async def main() -> int:
    """Главная функция."""
    args = parse_args()

    # Настроить логирование
    log_level_map = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
    }
    log_config = LogConfig(
        level=log_level_map[args.log_level],
        format=LogFormat.TEXT,
        colorize=not args.no_color,
    )
    setup_logging(log_config)

    # Создать handler
    handler = EchoHandler(
        pretty=args.pretty,
        show_schema=args.show_schema,
        filter_table=args.filter_table,
        no_color=args.no_color,
    )

    # Определить offset specification
    if args.offset is not None:
        offset_spec = ConsumerOffsetSpecification(OffsetType.OFFSET, args.offset)
        logger.info("Starting from offset={offset}", offset=args.offset)
    elif args.offset_last:
        offset_spec = ConsumerOffsetSpecification(OffsetType.LAST)
        logger.info("Starting from last offset")
    else:
        offset_spec = ConsumerOffsetSpecification(OffsetType.FIRST)
        logger.info("Starting from first offset")

    # Создать consumer
    consumer = EchoConsumer(
        stream=args.stream,
        host=args.host,
        port=args.port,
        vhost=args.vhost,
        username=args.user,
        password=args.password,
        offset_spec=offset_spec,
        handler=handler,
    )

    # Настроить graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_manager = GracefulShutdown()
    shutdown_manager.setup(loop)

    try:
        # Запустить consumer
        await consumer.start()

        # Создать задачу для consumer.run()
        run_task = asyncio.create_task(consumer.run())

        # Ожидать shutdown signal или завершения run_task
        done, pending = await asyncio.wait(
            [run_task, asyncio.create_task(shutdown_manager.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Остановить consumer
        await consumer.stop()

        # Отменить незавершенные задачи
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Вывести статистику
        handler.print_statistics()

        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        await consumer.stop()
        handler.print_statistics()
        return 0
    except Exception as e:
        logger.exception("Fatal error: {error}", error=str(e))
        return 1
    finally:
        shutdown_manager.restore()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
