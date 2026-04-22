# ruff: noqa: D100, D101, D102
from collections.abc import Mapping, Sequence
from typing import Any

import msgspec
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.types import Matrix

from src.core.repository import ClickHouseSessionProtocol


class ClickHouseSession(ClickHouseSessionProtocol):
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def fetch(
        self,
        query: str,
        parameters: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Matrix:
        result = await self._client.query(query, parameters=parameters)
        return result.result_rows

    async def fetch_one(
        self,
        query: str,
        parameters: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Mapping[str, Any] | Sequence[Any] | msgspec.Struct | None:
        rows = await self.fetch(query, parameters)
        return rows[0] if rows else None

    async def execute(
        self,
        query: str,
        parameters: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        return await self._client.command(query, parameters=parameters)

    async def insert(
        self,
        table: str,
        column_names: Sequence[str],
        data: Sequence[Sequence[Any]],
        settings: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._client.insert(
            table=table,
            column_names=column_names,
            data=data,
            settings=dict(settings) if settings is not None else None,
        )

    @property
    def database(self) -> str:
        database = self._client.get_client_setting("database") or "default"
        return database
