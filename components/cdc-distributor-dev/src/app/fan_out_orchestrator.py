"""Оркестратор публикации CDC агрегатов в очередь одного борта."""

from collections.abc import Callable

import msgspec
from loguru import logger

from src.app.amqp_publisher import AMQPPublisher
from src.app.bort_offset_manager import BortOffsetManager
from src.app.model import Envelope
from src.app.model.fan_out_payload import FanOutPayload, TableBatch
from src.app.multi_table_aggregator import MultiTableAggregator


class FanOutOrchestrator:
    """Оркестратор публикации в очередь одного борта.

    Заменяет MultiTableApplyOrchestrator. Вместо применения в БД,
    агрегирует CDC-события, сериализует в JSON и публикует
    в очередь конкретного борта.

    Каждый (bort x service) consumer получает свой экземпляр
    FanOutOrchestrator с фиксированным bort_id.
    Изоляция отказов достигается структурно —
    отдельные consumer'ы не влияют друг на друга.

    Гарантии:
    - Offset продвигается только после успешного publisher confirm
    - Structured logging на каждый publish с контекстом
    - Idempotent payload: CdcAggregator does last-write-wins by ID
    """

    def __init__(
        self,
        *,
        aggregator: MultiTableAggregator,
        publisher: AMQPPublisher,
        offset_manager: BortOffsetManager,
        bort_id: int,
        service_name: str,
        seq_id: int,
        on_seq_advance: Callable[[], None] | None = None,
    ) -> None:
        self._aggregator = aggregator
        self._publisher = publisher
        self._offset_manager = offset_manager
        self._bort_id = bort_id
        self._service_name = service_name
        self._seq_id = seq_id
        self._on_seq_advance = on_seq_advance

    async def process_batch(
        self,
        events: list[Envelope],
        stream_name: str,
        max_offset: int,
        min_offset: int,
    ) -> None:
        """Обрабатывает батч CDC-событий: агрегация -> сериализация -> publish.

        Args:
            events: список CDC-событий из стрима
            stream_name: имя RabbitMQ стрима
            max_offset: максимальный offset в батче
            min_offset: минимальный offset в батче
        """
        # 1. Агрегация по таблицам (last-write-wins)
        batches_by_table = self._aggregator.aggregate(events)

        logger.info(
            "Processing batch bort={bort} stream={stream} "
            "events={events} tables={tables} offsets={low}-{up}",
            bort=self._bort_id,
            stream=stream_name,
            events=len(events),
            tables=list(batches_by_table.keys()),
            low=min_offset,
            up=max_offset,
        )

        # 2. Конвертация AggregatedBatch в TableBatch для сериализации
        tables_payload: dict[str, TableBatch] = {}
        for table_name, batch in batches_by_table.items():
            tables_payload[table_name] = TableBatch(
                upserts=batch.upserts,
                deletes=batch.deletes,
            )

        # 3. Собираем payload
        payload = FanOutPayload(
            seq_id=self._seq_id,
            low_offset=min_offset,
            up_offset=max_offset,
            tables=tables_payload,
        )

        # 4. Сериализация
        body: bytes = msgspec.json.encode(payload)

        # 5. Публикация с retry (AMQPPublisher обрабатывает retry внутри)
        try:
            await self._publisher.publish(
                bort_id=self._bort_id,
                service_name=self._service_name,
                body=body,
            )
        except Exception:
            # Log error, do NOT save offset, do NOT advance seq_id.
            # The consumer's rstream position does not advance because
            # we re-raise the exception (handler fails, no offset commit).
            logger.error(
                "Fan-out failed target_id={bort} service={service} "
                "batch_offset={offset} result=error",
                bort=self._bort_id,
                service=self._service_name,
                offset=max_offset,
            )
            raise

        # 6. Offset и seq_id сохраняются ТОЛЬКО после успешного publisher confirm
        await self._offset_manager.save_offset(
            stream_name=stream_name,
            bort_id=self._bort_id,
            offset=max_offset,
            seq_id=self._seq_id,
        )

        # 7. Инкремент seq_id после успешной публикации
        self._seq_id += 1
        if self._on_seq_advance is not None:
            self._on_seq_advance()

        # Structured log with all required context
        logger.info(
            "Fan-out ok target_id={bort} service={service} batch_offset={offset} result=ok",
            bort=self._bort_id,
            service=self._service_name,
            offset=max_offset,
        )
