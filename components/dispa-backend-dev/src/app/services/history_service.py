"""Сервис объединённой истории машины с телеметрией."""

from bisect import bisect_left
from datetime import UTC, datetime, timedelta

from platform_sdk import (
    AsyncClients,
    ClientSettings,
    CycleTagHistoryField,
    FilterGroup,
    FilterParam,
    FilterType,
    QueryOperator,
    VehicleTelemetryField,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.event_log import CycleStateHistoryResponse
from app.api.schemas.history.history import (
    HistoryEventType,
    HistoryItem,
    StateHistoryItem,
    TagHistoryItem,
    VehicleTelemetry,
)
from app.core.config import settings
from app.database import CycleStateHistory

TELEMETRY_MAX_DELTA = timedelta(minutes=5)

analytics_client_settings = ClientSettings(
    base_url=settings.analytics_service_url,
)


class HistoryService:
    """Строит объединённую историю событий машины и прикрепляет телеметрию."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def get_state_history(
        self,
        vehicle_id: int,
        from_datetime: datetime,
        to_datetime: datetime,
    ) -> list[StateHistoryItem]:
        """Вернуть историю состояний State Machine из БД в заданном диапазоне."""
        query = (
            select(CycleStateHistory)
            .where(
                CycleStateHistory.vehicle_id == vehicle_id,
                CycleStateHistory.timestamp >= from_datetime,
                CycleStateHistory.timestamp <= to_datetime,
            )
            .order_by(CycleStateHistory.timestamp)
        )
        result = await self.db_session.execute(query)
        return [StateHistoryItem(data=CycleStateHistoryResponse.model_validate(row)) for row in result.scalars().all()]

    @classmethod
    async def get_tag_history(
        cls,
        vehicle_id: int,
        from_datetime: datetime,
        to_datetime: datetime,
    ) -> list[TagHistoryItem]:
        """Вернуть историю меток локации из analytics-сервиса в заданном диапазоне."""
        filters = FilterGroup[CycleTagHistoryField](
            type=FilterType.AND,
            items=[
                FilterParam[CycleTagHistoryField](
                    field=CycleTagHistoryField.VEHICLE_ID,
                    value=vehicle_id,
                    operator=QueryOperator.EQUALS,
                ),
                FilterParam[CycleTagHistoryField](
                    field=CycleTagHistoryField.TIMESTAMP,
                    value=from_datetime.isoformat(),
                    operator=QueryOperator.EQUALS_OR_GREATER,
                ),
                FilterParam[CycleTagHistoryField](
                    field=CycleTagHistoryField.TIMESTAMP,
                    value=to_datetime.isoformat(),
                    operator=QueryOperator.EQUALS_OR_LESS,
                ),
            ],
        )

        async with AsyncClients(analytics_client_settings) as clients:
            first_page = await clients.analytics.get_cycle_tag_history(
                root=filters,
                limit=1,
                sort_by=CycleTagHistoryField.TIMESTAMP,
            )
            if first_page.total_count == 0:
                return []
            response = await clients.analytics.get_cycle_tag_history(
                root=filters,
                limit=first_page.total_count,
                sort_by=CycleTagHistoryField.TIMESTAMP,
            )
        return [TagHistoryItem(data=item) for item in response.data]

    async def get_history(
        self,
        vehicle_id: int,
        from_datetime: datetime,
        to_datetime: datetime,
        event_types: list[HistoryEventType] | None = None,
    ) -> list[HistoryItem]:
        """Собрать единую историю (состояния + метки) и прицепить к каждому событию телеметрию."""
        wanted = set(event_types) if event_types else set(HistoryEventType)

        merged: list[HistoryItem] = []
        if HistoryEventType.state_history in wanted:
            merged.extend(await self.get_state_history(vehicle_id, from_datetime, to_datetime))
        if HistoryEventType.tag_history in wanted:
            merged.extend(await self.get_tag_history(vehicle_id, from_datetime, to_datetime))

        merged.sort(key=lambda item: _as_utc(item.data.timestamp))

        if merged:
            await self._attach_telemetry(vehicle_id, merged)

        return merged

    async def _attach_telemetry(self, vehicle_id: int, items: list[HistoryItem]) -> None:
        min_ts = _as_utc(items[0].data.timestamp) - TELEMETRY_MAX_DELTA
        max_ts = _as_utc(items[-1].data.timestamp) + TELEMETRY_MAX_DELTA
        telemetry = await self._fetch_telemetry(vehicle_id, min_ts, max_ts)
        if not telemetry:
            return

        tel_ts = [_as_utc(t.timestamp) for t in telemetry]
        for item in items:
            ts = _as_utc(item.data.timestamp)
            idx = bisect_left(tel_ts, ts)
            candidates = [i for i in (idx - 1, idx) if 0 <= i < len(telemetry)]
            if not candidates:
                continue
            nearest_idx = min(candidates, key=lambda i: abs(tel_ts[i] - ts))
            if abs(tel_ts[nearest_idx] - ts) <= TELEMETRY_MAX_DELTA:
                item.telemetry = telemetry[nearest_idx]

    @staticmethod
    async def _fetch_telemetry(
        vehicle_id: int,
        from_datetime: datetime,
        to_datetime: datetime,
    ) -> list[VehicleTelemetry]:
        filters = FilterGroup[VehicleTelemetryField](
            type=FilterType.AND,
            items=[
                FilterParam[VehicleTelemetryField](
                    field=VehicleTelemetryField.BORT,
                    value=vehicle_id,
                    operator=QueryOperator.EQUALS,
                ),
                FilterParam[VehicleTelemetryField](
                    field=VehicleTelemetryField.TIMESTAMP,
                    value=from_datetime.isoformat(),
                    operator=QueryOperator.EQUALS_OR_GREATER,
                ),
                FilterParam[VehicleTelemetryField](
                    field=VehicleTelemetryField.TIMESTAMP,
                    value=to_datetime.isoformat(),
                    operator=QueryOperator.EQUALS_OR_LESS,
                ),
            ],
        )
        async with AsyncClients(analytics_client_settings) as clients:
            first_page = await clients.analytics.get_vehicle_telemetry(
                root=filters,
                limit=1,
                sort_by=VehicleTelemetryField.TIMESTAMP,
            )
            if first_page.total_count == 0:
                return []
            response = await clients.analytics.get_vehicle_telemetry(
                root=filters,
                limit=first_page.total_count,
                sort_by=VehicleTelemetryField.TIMESTAMP,
            )
        return [
            VehicleTelemetry(
                timestamp=item.timestamp,
                lon=item.lon,
                lat=item.lat,
                fuel=item.fuel,
                speed=item.speed,
                height=item.height,
            )
            for item in response.data
        ]


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
