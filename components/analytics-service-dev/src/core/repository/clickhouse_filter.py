# ruff: noqa: D100, D101, D103
"""Построитель WHERE-условий для ClickHouse из FilterRequest (chain-стиль)."""

from datetime import date, datetime
from typing import Any

from src.core.filter.type import QueryOperator

_OPERATOR_MAP: dict[QueryOperator, str] = {
    QueryOperator.EQUALS: "=",
    QueryOperator.NOT_EQUAL: "!=",
    QueryOperator.GREATER: ">",
    QueryOperator.EQUALS_OR_GREATER: ">=",
    QueryOperator.LESS: "<",
    QueryOperator.EQUALS_OR_LESS: "<=",
    QueryOperator.IN: "IN",
    QueryOperator.NOT_IN: "NOT IN",
    QueryOperator.STARTS_WITH: "LIKE",
    QueryOperator.NOT_START_WITH: "NOT LIKE",
    QueryOperator.ENDS_WITH: "LIKE",
    QueryOperator.NOT_END_WITH: "NOT LIKE",
    QueryOperator.CONTAINS: "LIKE",
    QueryOperator.NOT_CONTAIN: "NOT LIKE",
}


def _like_value(operator: QueryOperator, value: str) -> str:
    if operator in (QueryOperator.STARTS_WITH, QueryOperator.NOT_START_WITH):
        return f"{value}%"
    if operator in (QueryOperator.ENDS_WITH, QueryOperator.NOT_END_WITH):
        return f"%{value}"
    return f"%{value}%"


def _coerce(value: Any, target_type: type) -> Any:
    """Приводит значение к целевому типу поля.

    Для datetime/date конструктор ждёт (year, month, day, ...), а не ISO-строку,
    поэтому такие типы парсим через .fromisoformat().
    """
    if isinstance(value, target_type):
        return value
    if isinstance(value, list):
        return [_coerce(v, target_type) for v in value]
    if target_type is datetime:
        return datetime.fromisoformat(str(value))
    if target_type is date:
        return date.fromisoformat(str(value))
    return target_type(value)


class _Counter:
    def __init__(self) -> None:
        self._n = 0

    def next(self) -> str:
        self._n += 1
        return f"p{self._n}"


def _build_node(
    node: Any,
    allowed_fields: frozenset[str],
    field_types: dict[str, type],
    counter: _Counter,
    params: dict[str, Any],
) -> str:
    kind = getattr(node, "kind", None)

    if kind == "param":
        field = str(node.field)
        if field not in allowed_fields:
            msg = f"Field '{field}' is not allowed for filtering"
            raise ValueError(msg)

        sql_op = _OPERATOR_MAP[node.operator]
        key = counter.next()
        value = node.value

        # Приводим тип значения к типу поля в ClickHouse
        target = field_types.get(field)
        if target is not None and value is not None:
            value = _coerce(value, target)

        if node.operator in (QueryOperator.IN, QueryOperator.NOT_IN):
            params[key] = list(value) if not isinstance(value, list) else value
            return f"{field} {sql_op} %({key})s"

        if node.operator in (
            QueryOperator.STARTS_WITH,
            QueryOperator.NOT_START_WITH,
            QueryOperator.ENDS_WITH,
            QueryOperator.NOT_END_WITH,
            QueryOperator.CONTAINS,
            QueryOperator.NOT_CONTAIN,
        ):
            value = _like_value(node.operator, str(value))

        params[key] = value
        return f"{field} {sql_op} %({key})s"

    if kind == "group":
        parts = [
            _build_node(item, allowed_fields, field_types, counter, params) for item in node.items
        ]
        joiner = f" {node.type.value} "
        return f"({joiner.join(parts)})"

    msg = f"Unknown filter node type: {type(node)}"
    raise TypeError(msg)


def build_where_clause(
    filter_request: Any,
    allowed_fields: frozenset[str],
    field_types: dict[str, type] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Строит WHERE-часть SQL и словарь параметров из FilterRequest.

    Args:
        filter_request: Запрос с деревом фильтров (должен иметь .chain).
        allowed_fields: Множество допустимых имён полей (whitelist).
        field_types: Маппинг имени поля на python-тип для приведения значений.

    Returns:
        (where_sql, params) — строка вида "WHERE ..." и словарь параметров.
    """
    params: dict[str, Any] = {}
    counter = _Counter()
    sql = _build_node(
        filter_request.chain,
        allowed_fields,
        field_types or {},
        counter,
        params,
    )
    return f"WHERE {sql}", params
