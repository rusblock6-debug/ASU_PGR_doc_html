"""Handler для CDC стрима enterprise-service с per-bort fan-out."""

from src.app.factories.enterpise import EnterpriseFactory
from src.app.model import Envelope
from src.core.rstream import StreamRouter
from src.core.rstream.router import BatchMetadata

router = StreamRouter()


@router.subscribe(
    "cdc-enterprise-service",
    event_type=Envelope,
    batch_size=1000,
    timeout=5,
)
async def enterprise_cdc_processor(
    events: list[Envelope],
    batch_metadata: BatchMetadata,
) -> None:
    """Обрабатывает CDC события enterprise-service."""
    from src.core.rstream.app import get_current_app

    app = get_current_app()
    factory: EnterpriseFactory = app.state  # type: ignore[assignment]

    aggregator = factory.get_multi_table_aggregator()
    orchestrator = await factory.create_fan_out_orchestrator(
        aggregator,
        batch_metadata.stream_name,
    )

    await orchestrator.process_batch(
        events=events,
        stream_name=batch_metadata.stream_name,
        max_offset=batch_metadata.max_offset,
        min_offset=batch_metadata.min_offset,
    )
