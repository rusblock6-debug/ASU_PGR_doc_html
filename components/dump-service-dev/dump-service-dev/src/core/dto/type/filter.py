# ruff: noqa: D100, D101

from enum import StrEnum


class FilterType(StrEnum):
    AND = "AND"
    OR = "OR"
