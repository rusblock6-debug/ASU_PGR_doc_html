"""Base factory для per-bort fan-out publishers."""

from src.app.amqp_publisher import AMQPPublisher
from src.app.bort_offset_manager import BortOffsetManager
from src.app.fan_out_orchestrator import FanOutOrchestrator
from src.app.multi_table_aggregator import MultiTableAggregator


class ServiceFactory:
    """Factory для создания aggregators и FanOutOrchestrator для одного борта.

    Per D-03/D-04: каждый (bort x service) consumer получает свой ServiceFactory
    с фиксированным bort_id.
    """

    def __init__(
        self,
        *,
        publisher: AMQPPublisher,
        offset_manager: BortOffsetManager,
        bort_id: int,
        service_name: str,
    ) -> None:
        self._publisher = publisher
        self._offset_manager = offset_manager
        self._bort_id = bort_id
        self._service_name = service_name
        self._seq_id: int | None = None

    async def _load_seq_id(self, stream_name: str) -> int:
        """Загружает seq_id из БД при первом вызове, потом возвращает кэш."""
        if self._seq_id is None:
            saved = await self._offset_manager.get_seq_id(
                stream_name,
                self._bort_id,
            )
            self._seq_id = (saved or 0) + 1
        return self._seq_id

    def advance_seq_id(self) -> None:
        """Инкрементирует seq_id после успешной публикации."""
        if self._seq_id is not None:
            self._seq_id += 1

    async def create_fan_out_orchestrator(
        self,
        aggregator: MultiTableAggregator,
        stream_name: str,
    ) -> FanOutOrchestrator:
        """Создает FanOutOrchestrator для данного борта и сервиса."""
        seq_id = await self._load_seq_id(stream_name)
        return FanOutOrchestrator(
            aggregator=aggregator,
            publisher=self._publisher,
            offset_manager=self._offset_manager,
            bort_id=self._bort_id,
            service_name=self._service_name,
            seq_id=seq_id,
            on_seq_advance=self.advance_seq_id,
        )
