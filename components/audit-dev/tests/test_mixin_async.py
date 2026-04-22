"""Tests for AuditMixin with async SQLAlchemy sessions (AsyncSession + asyncpg)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any, ClassVar

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from audit_lib.config import configure_audit, reset_config
from audit_lib.context import set_audit_context, set_audit_user
from audit_lib.mixin import AuditMixin
from audit_lib.models import create_audit_model
from tests.conftest import PG_ASYNC_URL

# ── Test schema ──────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


AuditOutbox = create_audit_model(Base)


class User(Base, AuditMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    email: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    __audit_exclude__: ClassVar[set[str]] = {"password_hash"}


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _configure_audit() -> Generator[None]:
    """Ensure AuditOutbox is configured for the mixin."""
    reset_config()
    configure_audit(Base)
    yield
    reset_config()


@pytest.fixture()
async def async_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(PG_ASYNC_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def async_session(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(async_engine) as session:
        yield session


# ── Helpers ──────────────────────────────────────────────────────────────


async def _outbox_records(session: AsyncSession) -> list[Any]:
    result = await session.execute(sa.select(AuditOutbox))
    return list(result.scalars())


# ── INSERT tests ─────────────────────────────────────────────────────────


async def test_async_insert_creates_audit_record(async_session: AsyncSession) -> None:
    """Async session: INSERT creates an outbox record with operation='create'."""
    user = User(name="Alice", email="alice@example.com")
    async_session.add(user)
    await async_session.flush()
    user_id = user.id
    await async_session.commit()

    records = await _outbox_records(async_session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "create"
    assert rec.entity_type == "users"
    assert rec.entity_id == str(user_id)
    assert rec.old_values is None
    assert rec.new_values is not None
    assert rec.new_values["name"] == "Alice"
    assert rec.new_values["email"] == "alice@example.com"
    assert isinstance(rec.id, uuid.UUID)
    assert rec.id.version == 7


# ── UPDATE tests ─────────────────────────────────────────────────────────


async def test_async_update_email_diff(async_session: AsyncSession) -> None:
    """Async session: UPDATE User.email produces correct diff in outbox."""
    user = User(name="Alice", email="alice@example.com")
    async_session.add(user)
    await async_session.commit()

    # Clear insert audit record
    for r in await _outbox_records(async_session):
        await async_session.delete(r)
    await async_session.commit()

    user.email = "bob@example.com"
    await async_session.commit()

    records = await _outbox_records(async_session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "update"
    assert rec.old_values == {"email": "alice@example.com"}
    assert rec.new_values == {"email": "bob@example.com"}


# ── DELETE tests ─────────────────────────────────────────────────────────


async def test_async_delete_creates_audit_record(async_session: AsyncSession) -> None:
    """Async session: DELETE creates an outbox record with old_values."""
    user = User(name="Alice", email="alice@example.com")
    async_session.add(user)
    await async_session.flush()
    user_id = user.id
    await async_session.commit()

    for r in await _outbox_records(async_session):
        await async_session.delete(r)
    await async_session.commit()

    await async_session.delete(user)
    await async_session.commit()

    records = await _outbox_records(async_session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "delete"
    assert rec.entity_id == str(user_id)
    assert rec.new_values is None
    assert rec.old_values is not None
    assert rec.old_values["name"] == "Alice"


# ── Same-transaction verification ────────────────────────────────────────


async def test_async_outbox_in_same_transaction(
    async_engine: AsyncEngine,
) -> None:
    """AuditOutbox record written within the same async transaction."""
    async with AsyncSession(async_engine) as session:
        user = User(name="Alice")
        session.add(user)
        await session.flush()

        # After flush (before commit), the outbox record should be visible.
        records = list((await session.execute(sa.select(AuditOutbox))).scalars())
        assert len(records) == 1
        assert records[0].operation == "create"

        await session.rollback()

    # After rollback, nothing persisted.
    async with AsyncSession(async_engine) as session:
        records = list((await session.execute(sa.select(AuditOutbox))).scalars())
        assert len(records) == 0


# ── Rollback negative case ──────────────────────────────────────────────


async def test_async_rollback_rolls_back_outbox(
    async_engine: AsyncEngine,
) -> None:
    """Rollback of async session also rolls back the outbox record."""
    async with AsyncSession(async_engine) as session:
        user = User(name="RollbackUser")
        session.add(user)
        await session.flush()

        # Outbox record exists mid-transaction
        records = list((await session.execute(sa.select(AuditOutbox))).scalars())
        assert len(records) == 1

        await session.rollback()

    # After rollback, both user and outbox record are gone.
    async with AsyncSession(async_engine) as session:
        users = list((await session.execute(sa.select(User))).scalars())
        assert len(users) == 0
        records = list((await session.execute(sa.select(AuditOutbox))).scalars())
        assert len(records) == 0


# ── Context integration ─────────────────────────────────────────────────


async def test_async_user_context(async_session: AsyncSession) -> None:
    """Async session respects audit context (user_id / service_name)."""
    async with set_audit_context(user_id="user-99", service_name="orders"):
        user = User(name="Alice")
        async_session.add(user)
        await async_session.commit()

    rec = (await _outbox_records(async_session))[0]
    assert rec.user_id == "user-99"
    assert rec.service_name == "orders"


async def test_async_set_audit_user(async_session: AsyncSession) -> None:
    """Async session with set_audit_user context manager."""
    async with set_audit_user("user-55"):
        user = User(name="Bob")
        async_session.add(user)
        await async_session.commit()

    rec = (await _outbox_records(async_session))[0]
    assert rec.user_id == "user-55"
