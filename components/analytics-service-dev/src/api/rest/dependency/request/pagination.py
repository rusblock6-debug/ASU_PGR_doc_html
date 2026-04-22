"""Pagination Dependency."""

from src.core.dto.type.pagination import PaginationParams


def get_pagination_params(
    skip: int = 0,
    limit: int = 100,
) -> PaginationParams:
    """Return Pydantic scheme from Depends() for pagination."""
    return PaginationParams(skip=skip, limit=limit)
