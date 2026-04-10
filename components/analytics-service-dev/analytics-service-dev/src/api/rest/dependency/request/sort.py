"""Sort Dependency."""

from src.core.dto.type.sort import SortParams, SortTypeEnum


def get_sort_params(
    sort_by: str | None = None,
    sort_type: SortTypeEnum | None = SortTypeEnum.asc,
) -> SortParams:
    """Return Pydantic scheme from Depends() for sort parameters."""
    return SortParams(sort_by=sort_by, sort_type=sort_type)
