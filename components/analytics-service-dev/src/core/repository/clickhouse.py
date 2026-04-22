# ruff: noqa: W505, S608
# mypy: disable-error-code="name-defined,valid-type"
"""Базовый ClickHouse репозиторий, работающий с msgspec DTO."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol, cast

import msgspec
from msgspec.structs import asdict

QueryParams = Sequence[Any] | dict[str, Any] | None
RowData = Mapping[str, Any] | Sequence[Any] | msgspec.Struct


class ClickHouseSessionProtocol(Protocol):
    """Контракт для ClickHouse сессии."""

    async def fetch(self, query: str, parameters: QueryParams = None) -> Sequence[RowData]:
        """Выполняет SELECT запрос и возвращает строки."""

    async def fetch_one(self, query: str, parameters: QueryParams = None) -> RowData | None:
        """Выполняет SELECT запрос и возвращает одну строку."""

    async def execute(self, query: str, parameters: QueryParams = None) -> Any:
        """Выполняет запрос без возврата строк (DDL/DML)."""

    async def insert(
        self,
        table: str,
        column_names: Sequence[str],
        data: Sequence[Sequence[Any]],
        settings: Mapping[str, Any] | None = None,
    ) -> Any:
        """Выполняет вставку данных построчно."""

    @property
    def database(self) -> str:
        """Возвращает имя базы от коннекта."""


class DTOValidationError(ValueError):
    """Ошибка преобразования данных в msgspec DTO."""


class ClickHouseRepository[ModelType: msgspec.Struct]:
    """Базовый репозиторий, который обменивается данными через msgspec DTO."""

    def __init__(self, dto_model: type[ModelType], session: ClickHouseSessionProtocol):
        self.model_class = dto_model
        self.session = session
        info = cast(Any, msgspec.inspect.type_info(dto_model))
        self._field_names: tuple[str, ...] = tuple(field.name for field in info.fields)

    async def fetch_all(
        self,
        query: str,
        parameters: QueryParams = None,
    ) -> list[ModelType]:
        """Выполняет запрос и преобразует все строки в DTO."""
        rows = await self.session.fetch(query=query, parameters=parameters)
        return [self._decode(row) for row in rows]

    async def fetch_one(
        self,
        query: str,
        parameters: QueryParams = None,
    ) -> ModelType | None:
        """Выполняет запрос и возвращает единственную DTO либо None."""
        row = await self.session.fetch_one(query=query, parameters=parameters)
        if row is None:
            return None
        return self._decode(row)

    async def execute(
        self,
        query: str,
        parameters: QueryParams = None,
    ) -> Any:
        """Выполняет запрос, не требующий преобразования в DTO."""
        return await self.session.execute(query=query, parameters=parameters)

    @classmethod
    def _encode(cls, dto: ModelType) -> dict[str, Any]:
        """Преобразует DTO в словарь для передачи в драйвер."""
        # msgspec.to_builtins() сериализует datetime в строки, что ломает
        # insert ClickHouse. asdict оставляет исходные python-объекты.
        return asdict(dto)

    def encode_many(self, dtos: Iterable[ModelType]) -> list[dict[str, Any]]:
        """Преобразует последовательность DTO в список словарей."""
        return [self._encode(dto) for dto in dtos]

    def _decode(self, data: RowData) -> ModelType:
        """Преобразует строку ClickHouse в DTO."""
        if isinstance(data, self.model_class):
            return data

        normalized = self._normalize_row(data)
        try:
            return msgspec.convert(normalized, type=self.model_class)
        except msgspec.ValidationError as exc:  # pragma: no cover - защитный блок
            raise DTOValidationError(
                f"Не удалось преобразовать данные в {self.model_class.__name__}: {exc}",
            ) from exc

    def _normalize_row(self, row: RowData) -> Mapping[str, Any]:
        """Приводит результат драйвера к формату dict[str, Any]."""
        if isinstance(row, Mapping):
            return row

        if isinstance(row, Sequence) and not isinstance(row, str | bytes | bytearray):
            values = list(row)
            if len(values) != len(self._field_names):
                raise DTOValidationError(
                    "Кол-во значений строки не соответствует DTO: "
                    f"{len(values)} != {len(self._field_names)}",
                )
            return dict(zip(self._field_names, values, strict=True))

        raise DTOValidationError(
            f"Неподдерживаемый тип данных: {type(row)!r} для {self.model_class.__name__}",
        )

    def _table_fqn(self) -> str:
        table = getattr(self.model_class, "__tablename__", None)
        if not table:
            raise ValueError(f"{self.model_class.__name__} must define __tablename__")

        # Если модель уже задаёт fully-qualified имя — не добавляем database повторно
        if "." in table:
            return table

        db = getattr(self.session, "database", None) or "default"
        return f"{db}.{table}"

    async def load_parquet(self, url: str) -> Any:
        """Загрузка .parquet файлов в clickhouse через url."""
        columns_sql = ", ".join(self._field_names)
        safe_url = url.replace("\\", "\\\\").replace("'", "\\'")

        query = f"""
            INSERT INTO {self._table_fqn()} ({columns_sql})
            SELECT {columns_sql}
            FROM url('{safe_url}', 'Parquet')
            SETTINGS http_make_head_request = 0
        """
        return await self.execute(query)

    async def create(
        self,
        model: ModelType,
        *,
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        """Вставляет одну запись DTO в таблицу модели."""
        await self.session.insert(
            table=self._table_fqn(),
            column_names=self._field_names,
            data=[self._prepare_values(model)],
            settings=settings,
        )

    def _prepare_values(self, model: ModelType | Mapping[str, Any]) -> list[Any]:
        """Возвращает значения модели в порядке колонок таблицы."""
        if isinstance(model, Mapping):
            source = model
        else:
            source = self._encode(model)
        return [source.get(name) for name in self._field_names]


__all__ = ["ClickHouseRepository", "ClickHouseSessionProtocol", "DTOValidationError"]
