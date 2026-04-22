from collections.abc import Mapping
from typing import Any

# ruff: noqa: D100, D101, S608
from src.app.model import S3File
from src.core.repository import ClickHouseRepository


class S3FileRepository(ClickHouseRepository[S3File]):
    async def create(
        self,
        model: S3File,
        *,
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        """Сохраняет обработанный файл с включённой async-вставкой."""
        async_settings: dict[str, Any] = {"async_insert": 1, "wait_for_async_insert": 1}
        merged_settings = dict(async_settings)
        if settings:
            merged_settings.update(settings)
        await super().create(model=model, settings=merged_settings)

    async def is_file_downloaded(self, object_key: str, etag: str) -> bool:
        """Checks if the file has been downloaded.

        :param object_key: object key.
        :param etag: etag value.
        :return: True if file has been downloaded, False otherwise.

        """
        query = f"""
            SELECT 1
            FROM {self._table_fqn()}
            WHERE object_key = %(object_key)s
              AND etag = %(etag)s
            LIMIT 1
        """
        row = await self.session.fetch_one(query, {"object_key": object_key, "etag": etag})
        return row is not None
