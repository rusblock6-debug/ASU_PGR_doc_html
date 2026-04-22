"""Репозитории для работы с БД."""

from .base import BaseRepository
from .sqlalchemy import SQLAlchemyRepository

__all__ = ["BaseRepository", "SQLAlchemyRepository"]
