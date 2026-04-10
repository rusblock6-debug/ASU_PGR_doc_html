# ruff: noqa: D100, D101
from datetime import datetime

from loguru import logger

from src.app.model import S3File
from src.app.repository import GpsDataRepository, S3FileRepository
from src.core.s3 import S3Client


class GpsDataController:
    def __init__(
        self,
        gps_data_repository: GpsDataRepository,
        s3_file_repository: S3FileRepository,
        s3_client: S3Client,
    ) -> None:
        self.gps_data_repository = gps_data_repository
        self.s3_file_repository = s3_file_repository
        self.s3_client = s3_client

    async def load(self, object_key: str, e_tag: str, filename: str) -> None:
        """Load GPS data from parquet file.

        :param object_key: object key.
        :param e_tag: etag value.
        :param filename: file name.
        :return: None.
        """
        if await self.s3_file_repository.is_file_downloaded(
            object_key,
            e_tag,
        ):
            logger.debug("{file} is already downloaded", file=object_key)
            return

        url = await self.s3_client.get_presigned_url(filename)
        await self.gps_data_repository.load_parquet(url)

        # сохраним что файл обработан
        await self.s3_file_repository.create(
            S3File(
                object_key=object_key,
                etag=e_tag,
                loaded_at=datetime.now(),
            ),
        )
