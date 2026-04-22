# ruff: noqa: D100, D101, D102
from datetime import datetime

from loguru import logger
from msgspec.structs import asdict

from src.app.model import S3File
from src.app.repository import S3FileRepository
from src.app.repository.cycle_tag_history import CycleTagHistoryRepository
from src.core.dto.scheme.response.pagination import PaginationResponse
from src.core.filter import FilterRequest
from src.core.s3 import S3Client


class CycleTagHistoryController:
    def __init__(
        self,
        cycle_tag_history_repository: CycleTagHistoryRepository,
        s3_file_repository: S3FileRepository | None = None,
        s3_client: S3Client | None = None,
    ) -> None:
        self.cycle_tag_history_repository = cycle_tag_history_repository
        self.s3_file_repository = s3_file_repository
        self.s3_client = s3_client

    async def get_by_filters(
        self,
        filter_request: FilterRequest | None = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: str | None = "asc",
    ) -> PaginationResponse:  # type: ignore[type-arg]
        data = await self.cycle_tag_history_repository.get_by_filters(
            filter_request=filter_request,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_type=sort_type,
        )
        total_count = await self.cycle_tag_history_repository.count(
            filter_request=filter_request,
        )
        page = skip // limit + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

        return PaginationResponse(
            data=[asdict(item) for item in data],
            page=page,
            page_size=len(data),
            total_pages=total_pages,
            total_count=total_count,
        )

    async def load(self, object_key: str, e_tag: str, filename: str) -> None:
        """Load file from trip_service parquet.

        :param object_key: object key.
        :param e_tag: etag value.
        :param filename: file name.
        :return: None.
        """
        if self.s3_file_repository is None or self.s3_client is None:
            logger.error("s3_file_repository and s3_client are required for load")
            return

        if await self.s3_file_repository.is_file_downloaded(object_key, e_tag):
            logger.debug("{file} is already downloaded", file=object_key)
            return

        url = await self.s3_client.get_presigned_url(filename)
        await self.cycle_tag_history_repository.load_parquet(url)

        await self.s3_file_repository.create(
            S3File(
                object_key=object_key,
                etag=e_tag,
                loaded_at=datetime.now(),
            ),
        )
