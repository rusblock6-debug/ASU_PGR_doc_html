from typing import Any

import asyncpg
from loguru import logger

from src.app.utils.type_converter import TypeConverter
from src.core.applier import Applier, ApplyResult
from src.core.aggregator import AggregatedBatch


class PostgresApplier(Applier[dict[str, Any]]):
    """
    Applier для PostgreSQL через asyncpg.

    Выполняет upsert и delete в одной транзакции с DEFERRABLE constraints.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        table: str,
        id_fields: list[str] | str = "id",
    ) -> None:
        self._pool = pool
        self._table = table

        # Нормализуем id_fields в список
        if isinstance(id_fields, str):
            self._id_fields = [id_fields]
        else:
            self._id_fields = id_fields

    async def apply(self, batch: AggregatedBatch[dict[str, Any]]) -> ApplyResult:
        if not batch.upserts and not batch.deletes:
            logger.debug("Empty batch, skipping table={table}", table=self._table)
            return ApplyResult(upserted=0, deleted=0)

        logger.debug(
            "Applying batch table={table} upserts={upserts} deletes={deletes}",
            table=self._table,
            upserts=len(batch.upserts),
            deletes=len(batch.deletes),
        )

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET CONSTRAINTS ALL DEFERRED")

                upserted = await self._upsert(conn, batch.upserts)
                deleted = await self._delete(conn, batch.deletes)

        logger.info(
            "Batch applied table={table} upserted={upserted} deleted={deleted}",
            table=self._table,
            upserted=upserted,
            deleted=deleted,
        )
        return ApplyResult(upserted=upserted, deleted=deleted)

    async def apply_in_transaction(
        self,
        conn: asyncpg.Connection,
        batch: AggregatedBatch[dict[str, Any]],
    ) -> ApplyResult:
        """
        Применяет батч используя существующее соединение/транзакцию.

        Используется когда несколько таблиц обрабатываются в одной транзакции.
        SET CONSTRAINTS ALL DEFERRED должен быть вызван вызывающей стороной.

        Args:
            conn: активное соединение с транзакцией
            batch: агрегированный батч для применения

        Returns:
            ApplyResult с результатами upsert/delete
        """
        upserted = await self._upsert(conn, batch.upserts)
        deleted = await self._delete(conn, batch.deletes)
        return ApplyResult(upserted=upserted, deleted=deleted)

    async def _upsert(
        self,
        conn: asyncpg.Connection,
        records: list[dict[str, Any]],
    ) -> int:
        if not records:
            return 0

        # Собираем все уникальные колонки из записей, исключая служебные поля __*
        columns: set[str] = set()
        for record in records:
            columns.update(k for k in record.keys() if not k.startswith("__"))

        columns_list = sorted(columns)
        placeholders = ", ".join(f"${i + 1}" for i in range(len(columns_list)))
        columns_str = ", ".join(f'"{col}"' for col in columns_list)

        # UPDATE SET для всех колонок кроме ключевых
        update_cols = [col for col in columns_list if col not in self._id_fields]

        # ON CONFLICT для составных ключей
        conflict_fields = ", ".join(f'"{field}"' for field in self._id_fields)

        # Если есть колонки для обновления - используем DO UPDATE SET
        # Если нет (только ключевые поля) - используем DO NOTHING
        if update_cols:
            update_set = ", ".join(f'"{col}" = EXCLUDED."{col}"' for col in update_cols)
            on_conflict = f"ON CONFLICT ({conflict_fields}) DO UPDATE SET {update_set}"
        else:
            # Таблица содержит только ключевые поля (например, junction table)
            on_conflict = f"ON CONFLICT ({conflict_fields}) DO NOTHING"

        query = f"""
            INSERT INTO {self._table} ({columns_str})
            VALUES ({placeholders})
            {on_conflict}
        """

        count = 0
        for record in records:
            values = [
                TypeConverter.convert_value(record.get(col), "", col)
                for col in columns_list
            ]
            await conn.execute(query, *values)
            count += 1

        return count

    async def _delete(
        self,
        conn: asyncpg.Connection,
        ids: list[Any],
    ) -> int:
        if not ids:
            return 0

        if len(self._id_fields) == 1:
            # Простой случай: один ключ
            query = f'DELETE FROM {self._table} WHERE "{self._id_fields[0]}" = $1'

            count = 0
            for record_id in ids:
                await conn.execute(query, record_id)
                count += 1
        else:
            # Составной ключ: WHERE user_id = $1 AND role_id = $2
            where_clauses = " AND ".join(
                f'"{field}" = ${i + 1}' for i, field in enumerate(self._id_fields)
            )
            query = f"DELETE FROM {self._table} WHERE {where_clauses}"

            count = 0
            for record_id in ids:
                # record_id должен быть tuple или dict
                if isinstance(record_id, dict):
                    values = [record_id[field] for field in self._id_fields]
                else:
                    values = list(record_id)

                await conn.execute(query, *values)
                count += 1

        return count
