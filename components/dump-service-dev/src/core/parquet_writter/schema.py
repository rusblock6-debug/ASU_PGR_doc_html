"""Helpers to derive pyarrow schemas and rows from Pydantic models."""

from datetime import date, datetime, time
from decimal import Decimal
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin

import pyarrow as pa
from pydantic import BaseModel

_PARQUET_FLATTEN_EXTRA = "parquet_flatten_root"


_PYDANTIC_SCALAR_TO_ARROW = {
    bool: pa.bool_(),
    int: pa.int64(),
    float: pa.float64(),
    str: pa.string(),
    datetime: pa.timestamp("us"),
    date: pa.date32(),
    time: pa.time64("us"),
    Decimal: pa.decimal128(38, 10),
}


def schema_from_model(
    model: type[BaseModel],
    *,
    prefix: str = "",
    path: tuple[str, ...] = (),
    rename: dict[tuple[str, ...], str] | None = None,
) -> pa.Schema:
    """Build a flat ``pa.Schema`` from a Pydantic model."""
    fields: list[pa.Field] = []
    for name, info in model.model_fields.items():
        annotation, nullable = _unwrap_optional(info.annotation)
        field_path = (*path, name)
        flatten_root = _should_flatten(info)
        field_name = _resolve_name(
            prefix,
            name,
            field_path,
            rename,
            flatten_root=flatten_root,
        )

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            nested_schema = schema_from_model(
                annotation,
                prefix=field_name,
                path=field_path,
                rename=rename,
            )
            fields.extend(nested_schema)
            continue

        field_type = _resolve_arrow_type(annotation)
        fields.append(
            pa.field(field_name, field_type, nullable=nullable or not info.is_required()),
        )

    return pa.schema(fields)


def flatten_model(
    instance: BaseModel,
    *,
    prefix: str = "",
    path: tuple[str, ...] = (),
    rename: dict[tuple[str, ...], str] | None = None,
) -> dict[str, Any]:
    """Convert a Pydantic model instance into a flat dict consistent with schema."""
    values: dict[str, Any] = {}
    model_cls = type(instance)
    for name, info in model_cls.model_fields.items():
        field_path = (*path, name)
        flatten_root = _should_flatten(info)
        field_name = _resolve_name(
            prefix,
            name,
            field_path,
            rename,
            flatten_root=flatten_root,
        )
        value = getattr(instance, name)
        annotation, _ = _unwrap_optional(info.annotation)

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if value is None:
                nested_schema = schema_from_model(
                    annotation,
                    prefix=field_name,
                    path=field_path,
                    rename=rename,
                )
                for nested_field in nested_schema.names:
                    values[nested_field] = None
                continue
            values.update(
                flatten_model(
                    value,
                    prefix=field_name,
                    path=field_path,
                    rename=rename,
                ),
            )
            continue

        if value is None:
            values[field_name] = None
            continue

        values[field_name] = value

    return values


def _join_prefix(prefix: str, name: str) -> str:
    return f"{prefix}_{name}" if prefix else name


def _resolve_name(
    prefix: str,
    name: str,
    path: tuple[str, ...],
    rename: dict[tuple[str, ...], str] | None,
    *,
    flatten_root: bool = False,
) -> str:
    if rename and path in rename:
        return rename[path]
    if flatten_root:
        return prefix
    return _join_prefix(prefix, name)


def _should_flatten(info: Any) -> bool:
    extra = getattr(info, "json_schema_extra", None) or {}
    return bool(extra.get(_PARQUET_FLATTEN_EXTRA))


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        args = [arg for arg in get_args(annotation) if arg is not NoneType]
        if len(args) == 1:
            return args[0], True
        return annotation, True
    return annotation, False


def _resolve_arrow_type(annotation: Any) -> pa.DataType:
    if annotation in _PYDANTIC_SCALAR_TO_ARROW:
        return _PYDANTIC_SCALAR_TO_ARROW[annotation]

    origin = get_origin(annotation)
    if origin in {list, tuple, set}:
        child = _resolve_arrow_type(get_args(annotation)[0])
        return pa.list_(child)

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        raise TypeError("Nested BaseModel should be flattened before resolving type")

    raise TypeError(f"Unsupported annotation {annotation!r} for Arrow schema")


__all__ = ["schema_from_model", "flatten_model"]
