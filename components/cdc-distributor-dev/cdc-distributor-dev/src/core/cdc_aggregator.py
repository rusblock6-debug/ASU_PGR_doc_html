"""CDC-агрегатор событий с логикой delete/upsert."""

from typing import Any

from .aggregator import AggregatedBatch, EventAggregator, HasPayload


class CdcAggregator[E: HasPayload](EventAggregator[E, dict[str, Any]]):
    """Агрегатор CDC событий.

    Группирует события по id:
    - delete побеждает всё
    - иначе last wins (последний upsert)
    """

    def __init__(
        self,
        id_field: str = "id",
        deleted_field: str = "__deleted",
    ) -> None:
        self._id_field = id_field
        self._deleted_field = deleted_field

    def aggregate(self, events: list[E]) -> AggregatedBatch[dict[str, Any]]:
        """Агрегирует список CDC событий в upserts и deletes."""
        grouped: dict[Any, dict[str, Any]] = {}
        deleted_ids: set[Any] = set()

        for event in events:
            payload = event.payload
            record_id = payload.get(self._id_field)

            if record_id is None:
                continue

            is_deleted = payload.get(self._deleted_field) == "true"

            if is_deleted:
                deleted_ids.add(record_id)
                grouped.pop(record_id, None)
            else:
                # INSERT/UPDATE после DELETE — INSERT побеждает
                deleted_ids.discard(record_id)
                grouped[record_id] = payload

        return AggregatedBatch(
            upserts=list(grouped.values()),
            deletes=list(deleted_ids),
        )
