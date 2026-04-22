# mypy: disable-error-code="attr-defined"
"""Core database."""

from .session import db_session
from .trip_session import trip_db_session

__all__ = ["db_session", "trip_db_session"]
