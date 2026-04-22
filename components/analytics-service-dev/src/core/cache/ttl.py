"""TTL для создания времени ttl."""

# ruff: noqa: D101
# mypy: disable-error-code="no-untyped-def,type-arg,union-attr,no-untyped-call"


class TTL:
    @staticmethod
    def time(hours: int = 0, minutes: int = 0, seconds: int = 0) -> int:
        """Метод для удобного создания ttl кеша."""
        return hours * 60 * 60 + minutes * 60 + seconds
