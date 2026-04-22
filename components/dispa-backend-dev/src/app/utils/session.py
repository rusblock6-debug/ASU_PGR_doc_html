"""Зависимости FastAPI: сессия БД."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session

SessionDepends = Annotated[AsyncSession, Depends(get_db_session)]
