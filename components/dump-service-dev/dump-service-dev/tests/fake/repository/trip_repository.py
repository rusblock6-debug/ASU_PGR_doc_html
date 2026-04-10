from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.repository import TripRepository


class FakeTripRepository(TripRepository):
    def __init__(
        self,
        db_session: AsyncSession,
        *,
        cycle_state_history: list[dict[str, Any]] | None = None,
        cycle_tag_history: list[dict[str, Any]] | None = None,
        cycles: list[dict[str, Any]] | None = None,
        cycle_analysis: list[dict[str, Any]] | None = None,
        trips: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(db_session)
        self._cycle_state_history = cycle_state_history or []
        self._cycle_tag_history = cycle_tag_history or []
        self._cycles = cycles or []
        self._trips = trips or []
        self._cycle_analytics = cycle_analysis or []

    @classmethod
    async def _aiter(cls, rows: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
        for row in rows:
            yield row

    def get_cycle_state_history(self, trip_id: str):
        return self._aiter(self._cycle_state_history)

    def get_cycle_tag_history(self, trip_id: str):
        return self._aiter(self._cycle_tag_history)

    def get_cycle(self, trip_id: str):
        return self._aiter(self._cycles)

    def get_cycle_analytics(self, trip_id: str):
        return self._aiter(self._cycle_analytics)

    def get_trip(self, trip_id: str):
        return self._aiter(self._trips)
