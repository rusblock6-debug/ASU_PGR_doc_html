# ruff: noqa: D100, D101, D102, S608
from datetime import datetime
from typing import Any

from src.app.model.cycle_tag_history import CycleTagHistory
from src.core.filter import FilterRequest
from src.core.repository import ClickHouseRepository
from src.core.repository.clickhouse_filter import build_where_clause

_ALLOWED_FIELDS = frozenset(CycleTagHistory.__struct_fields__)

_FIELD_TYPES: dict[str, type] = {
    "id": str,
    "timestamp": datetime,
    "vehicle_id": int,
    "cycle_id": str,
    "place_id": int,
    "place_name": str,
    "place_type": str,
    "tag_id": int,
    "tag_name": str,
    "tag_event": str,
}


class CycleTagHistoryRepository(ClickHouseRepository[CycleTagHistory]):
    async def get_by_filters(
        self,
        filter_request: FilterRequest | None = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_type: str | None = "asc",
    ) -> list[CycleTagHistory]:
        where_sql = ""
        params: dict[str, Any] = {}

        if filter_request is not None:
            where_sql, params = build_where_clause(filter_request, _ALLOWED_FIELDS, _FIELD_TYPES)

        order_sql = ""
        if sort_by and sort_by in _ALLOWED_FIELDS:
            direction = "DESC" if sort_type and sort_type.lower() == "desc" else "ASC"
            order_sql = f"ORDER BY {sort_by} {direction}"

        query = f"""
            SELECT *
            FROM {self._table_fqn()}
            {where_sql}
            {order_sql}
            LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = limit
        params["offset"] = skip

        return await self.fetch_all(query, params)

    async def count(
        self,
        filter_request: FilterRequest | None = None,
    ) -> int:
        where_sql = ""
        params: dict[str, Any] = {}

        if filter_request is not None:
            where_sql, params = build_where_clause(filter_request, _ALLOWED_FIELDS, _FIELD_TYPES)

        query = f"""
            SELECT count() AS cnt
            FROM {self._table_fqn()}
            {where_sql}
        """
        row = await self.session.fetch_one(query, params)
        if row is None:
            return 0
        return int(row["cnt"]) if isinstance(row, dict) else int(row[0])  # type: ignore[index]
