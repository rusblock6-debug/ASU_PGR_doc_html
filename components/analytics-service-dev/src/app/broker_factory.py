# ruff: noqa: D100, D101, D102
from functools import partial

from fast_depends import Depends

from src.app.controller import (
    CycleTagHistoryController,
    EkiperEventsController,
    GpsDataController,
)
from src.app.model import CycleTagHistory, EkiperEvent, GpsData, S3File
from src.app.repository import (
    CycleTagHistoryRepository,
    GpsDataRepository,
    S3FileRepository,
)
from src.app.repository.ekiper_events import EkiperEventsRepository
from src.core.clickhouse import ClickHouseSession, get_clickhouse_session
from src.core.s3 import S3Client, get_s3_client


class BrokerFactory:
    ekiper_events_repository = staticmethod(
        partial(
            EkiperEventsRepository,
            dto_model=EkiperEvent,
        ),
    )
    gps_data_repository = staticmethod(
        partial(
            GpsDataRepository,
            dto_model=GpsData,
        ),
    )
    cycle_tag_history_repository = staticmethod(
        partial(
            CycleTagHistoryRepository,
            dto_model=CycleTagHistory,
        ),
    )
    s3_file_repository = staticmethod(
        partial(
            S3FileRepository,
            dto_model=S3File,
        ),
    )

    @classmethod
    def get_ekiper_events_controller(
        cls,
        clickhouse_session: ClickHouseSession = Depends(get_clickhouse_session),
        s3_client: S3Client = Depends(get_s3_client),
    ) -> "EkiperEventsController":
        return EkiperEventsController(
            ekiper_events_repository=cls.ekiper_events_repository(
                session=clickhouse_session,
            ),
            s3_file_repository=cls.s3_file_repository(
                session=clickhouse_session,
            ),
            s3_client=s3_client,
        )

    @classmethod
    def get_gps_data_controller(
        cls,
        clickhouse_session: ClickHouseSession = Depends(get_clickhouse_session),
        s3_client: S3Client = Depends(get_s3_client),
    ) -> "GpsDataController":
        return GpsDataController(
            gps_data_repository=cls.gps_data_repository(
                session=clickhouse_session,
            ),
            s3_file_repository=cls.s3_file_repository(
                session=clickhouse_session,
            ),
            s3_client=s3_client,
        )

    @classmethod
    def get_cycle_tag_history_controller(
        cls,
        clickhouse_session: ClickHouseSession = Depends(get_clickhouse_session),
        s3_client: S3Client = Depends(get_s3_client),
    ) -> "CycleTagHistoryController":
        return CycleTagHistoryController(
            cycle_tag_history_repository=cls.cycle_tag_history_repository(
                session=clickhouse_session,
            ),
            s3_file_repository=cls.s3_file_repository(
                session=clickhouse_session,
            ),
            s3_client=s3_client,
        )
