# ruff: noqa: D100, D101, D102
from fastapi import Depends

from src.app.controller import CycleTagHistoryController, VehicleTelemetryController
from src.app.model import CycleTagHistory, VehicleTelemetry
from src.app.repository import CycleTagHistoryRepository, VehicleTelemetryRepository
from src.core.clickhouse import ClickHouseSession, get_clickhouse_session


class FastAPIFactory:
    @classmethod
    def get_vehicle_telemetry_controller(
        cls,
        clickhouse_session: ClickHouseSession = Depends(get_clickhouse_session),
    ) -> VehicleTelemetryController:
        return VehicleTelemetryController(
            vehicle_telemetry_repository=VehicleTelemetryRepository(
                dto_model=VehicleTelemetry,
                session=clickhouse_session,
            ),
        )

    @classmethod
    def get_cycle_tag_history_controller(
        cls,
        clickhouse_session: ClickHouseSession = Depends(get_clickhouse_session),
    ) -> CycleTagHistoryController:
        return CycleTagHistoryController(
            cycle_tag_history_repository=CycleTagHistoryRepository(
                dto_model=CycleTagHistory,
                session=clickhouse_session,
            ),
        )
