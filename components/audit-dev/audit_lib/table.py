"""Helpers for creating the audit_outbox table."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase

from audit_lib.models import create_audit_model


def create_audit_table(engine: sa.Engine) -> None:
    """Create the ``audit_outbox`` table if it does not already exist.

    Uses a temporary :class:`DeclarativeBase` to generate the DDL. Safe to
    call multiple times — the table is created with ``checkfirst=True``.

    Parameters
    ----------
    engine:
        A synchronous SQLAlchemy :class:`~sqlalchemy.engine.Engine`.

    Raises
    ------
    TypeError
        If *engine* is not a :class:`~sqlalchemy.engine.Engine`.
    """
    if not isinstance(engine, sa.Engine):
        msg = (
            f"Expected a sqlalchemy.Engine instance, "
            f"got {type(engine).__name__!r}."
        )
        raise TypeError(msg)

    class _TempBase(DeclarativeBase):
        pass

    create_audit_model(_TempBase)
    _TempBase.metadata.create_all(engine, checkfirst=True)


async def create_audit_table_async(async_engine: Any) -> None:
    """Create the ``audit_outbox`` table asynchronously.

    Async variant of :func:`create_audit_table`.

    Parameters
    ----------
    async_engine:
        A :class:`~sqlalchemy.ext.asyncio.AsyncEngine`.

    Raises
    ------
    TypeError
        If *async_engine* is not an ``AsyncEngine``.
    """
    from sqlalchemy.ext.asyncio import AsyncEngine

    if not isinstance(async_engine, AsyncEngine):
        msg = (
            f"Expected a sqlalchemy.ext.asyncio.AsyncEngine instance, "
            f"got {type(async_engine).__name__!r}."
        )
        raise TypeError(msg)

    class _TempBase(DeclarativeBase):
        pass

    create_audit_model(_TempBase)

    async with async_engine.begin() as conn:
        await conn.run_sync(_TempBase.metadata.create_all, checkfirst=True)
