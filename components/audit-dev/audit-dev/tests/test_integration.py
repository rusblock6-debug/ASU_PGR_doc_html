"""Integration tests for end-to-end audit flows (US-009)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any, ClassVar

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from audit_lib.config import configure_audit, reset_config
from audit_lib.context import set_audit_user
from audit_lib.mixin import AuditMixin
from audit_lib.models import create_audit_model
from tests.conftest import PG_ASYNC_URL, PG_SYNC_URL


class Base(DeclarativeBase):
    pass


AuditOutbox = create_audit_model(Base)


class IntegrationUser(Base, AuditMixin):
    __tablename__ = "integration_users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    email: Mapped[str] = mapped_column(sa.String, nullable=False)


class IntegrationOrder(Base, AuditMixin):
    __tablename__ = "integration_orders"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(sa.String, nullable=False)


class ExcludedProfile(Base, AuditMixin):
    __tablename__ = "excluded_profiles"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    secret_token: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    __audit_exclude__: ClassVar[set[str]] = {"secret_token"}


@pytest.fixture(autouse=True)
def _configure() -> Generator[None]:
    reset_config()
    configure_audit(Base)
    yield
    reset_config()


@pytest.fixture()
def engine() -> Generator[sa.Engine]:
    eng = sa.create_engine(PG_SYNC_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def session(engine: sa.Engine) -> Generator[Session]:
    with Session(engine) as sess:
        yield sess


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


def _outbox_for_entity(
    session: Session,
    *,
    entity_type: str,
    entity_id: str,
) -> list[Any]:
    stmt = (
        sa.select(AuditOutbox)
        .where(AuditOutbox.entity_type == entity_type)
        .where(AuditOutbox.entity_id == entity_id)
        .order_by(AuditOutbox.timestamp.asc())
    )
    return list(session.execute(stmt).scalars())


def test_full_crud_lifecycle_produces_expected_diffs(session: Session) -> None:
    with set_audit_user("user-crud"):
        user = IntegrationUser(name="Alice", email="alice@example.com")
        session.add(user)
        session.commit()
        user_id = user.id

        user.name = "Alice A."
        session.commit()

        user.email = "alice.new@example.com"
        session.commit()

        session.delete(user)
        session.commit()

    records = _outbox_for_entity(
        session,
        entity_type="integration_users",
        entity_id=str(user_id),
    )
    assert len(records) == 4
    assert [rec.operation for rec in records] == [
        "create",
        "update",
        "update",
        "delete",
    ]

    assert records[0].old_values is None
    assert records[0].new_values["name"] == "Alice"
    assert records[0].new_values["email"] == "alice@example.com"
    assert records[1].old_values == {"name": "Alice"}
    assert records[1].new_values == {"name": "Alice A."}
    assert records[2].old_values == {"email": "alice@example.com"}
    assert records[2].new_values == {"email": "alice.new@example.com"}
    assert records[3].new_values is None
    assert records[3].old_values["name"] == "Alice A."
    assert records[3].old_values["email"] == "alice.new@example.com"
    assert all(rec.user_id == "user-crud" for rec in records)


def test_multiple_models_same_session_each_gets_outbox_record(
    session: Session,
) -> None:
    with set_audit_user("user-multi"):
        user = IntegrationUser(name="Bob", email="bob@example.com")
        order = IntegrationOrder(order_no="ORD-001")
        session.add_all([user, order])
        session.commit()

    stmt = sa.select(AuditOutbox).order_by(AuditOutbox.timestamp.asc())
    records = list(session.execute(stmt).scalars())
    assert len(records) == 2
    assert {rec.entity_type for rec in records} == {
        "integration_users",
        "integration_orders",
    }
    assert all(rec.user_id == "user-multi" for rec in records)


def test_transaction_rollback_persists_no_outbox_records(
    engine: sa.Engine,
) -> None:
    with Session(engine) as session:
        user = IntegrationUser(name="Rollback", email="rollback@example.com")
        session.add(user)
        session.flush()

        in_tx_records = list(session.execute(sa.select(AuditOutbox)).scalars())
        assert len(in_tx_records) == 1

        session.rollback()

    with Session(engine) as session:
        assert session.scalar(
            sa.select(sa.func.count()).select_from(IntegrationUser)
        ) == 0
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditOutbox)) == 0


def test_user_id_from_context_is_recorded(session: Session) -> None:
    with set_audit_user("ctx-user-42"):
        user = IntegrationUser(name="Ctx", email="ctx@example.com")
        session.add(user)
        session.commit()

    rec = session.execute(sa.select(AuditOutbox)).scalar_one()
    assert rec.user_id == "ctx-user-42"


async def test_async_concurrent_operations_isolate_user_contexts(
    async_engine: AsyncEngine,
) -> None:
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    gate = asyncio.Event()
    ready = 0
    ready_lock = asyncio.Lock()

    async def worker(user_id: str, name: str) -> None:
        nonlocal ready
        async with set_audit_user(user_id):
            async with ready_lock:
                ready += 1
                if ready == 2:
                    gate.set()
            await gate.wait()
            async with session_factory() as session:
                session.add(
                    IntegrationUser(
                        name=name,
                        email=f"{name.lower()}@example.com",
                    )
                )
                await session.commit()

    await asyncio.gather(
        worker("async-user-a", "AsyncA"),
        worker("async-user-b", "AsyncB"),
    )

    async with session_factory() as session:
        stmt = (
            sa.select(AuditOutbox)
            .where(AuditOutbox.entity_type == "integration_users")
            .where(AuditOutbox.operation == "create")
        )
        records = list((await session.execute(stmt)).scalars())

    assert len(records) == 2
    name_to_user: dict[str, str | None] = {}
    for rec in records:
        assert rec.new_values is not None
        name_to_user[rec.new_values["name"]] = rec.user_id
    assert name_to_user == {
        "AsyncA": "async-user-a",
        "AsyncB": "async-user-b",
    }


def test_audit_exclude_omits_fields_for_create_update_delete(
    session: Session,
) -> None:
    profile = ExcludedProfile(
        display_name="Visible",
        secret_token="secret-1",
    )
    session.add(profile)
    session.commit()
    profile_id = profile.id

    profile.display_name = "Visible Updated"
    profile.secret_token = "secret-2"
    session.commit()

    session.delete(profile)
    session.commit()

    records = _outbox_for_entity(
        session,
        entity_type="excluded_profiles",
        entity_id=str(profile_id),
    )
    assert [rec.operation for rec in records] == ["create", "update", "delete"]

    create_rec, update_rec, delete_rec = records
    assert "secret_token" not in create_rec.new_values
    assert update_rec.old_values == {"display_name": "Visible"}
    assert update_rec.new_values == {"display_name": "Visible Updated"}
    assert "secret_token" not in update_rec.old_values
    assert "secret_token" not in update_rec.new_values
    assert "secret_token" not in delete_rec.old_values
    assert delete_rec.new_values is None


def test_bulk_insert_and_bulk_update_emit_outbox_records(
    session: Session,
) -> None:
    users = [
        IntegrationUser(name="Bulk1", email="bulk1@example.com"),
        IntegrationUser(name="Bulk2", email="bulk2@example.com"),
    ]
    session.add_all(users)
    session.commit()

    for user in users:
        user.email = f"updated-{user.name.lower()}@example.com"
    session.commit()

    stmt = (
        sa.select(AuditOutbox)
        .where(AuditOutbox.entity_type == "integration_users")
        .order_by(AuditOutbox.timestamp.asc())
    )
    records = list(session.execute(stmt).scalars())
    assert len(records) == 4
    assert [rec.operation for rec in records].count("create") == 2
    assert [rec.operation for rec in records].count("update") == 2

    expected_updates = {
        str(users[0].id): ("bulk1@example.com", "updated-bulk1@example.com"),
        str(users[1].id): ("bulk2@example.com", "updated-bulk2@example.com"),
    }
    update_records = [rec for rec in records if rec.operation == "update"]
    assert len(update_records) == 2
    for rec in update_records:
        old_email, new_email = expected_updates[rec.entity_id]
        assert rec.old_values == {"email": old_email}
        assert rec.new_values == {"email": new_email}


def test_outbox_diff_columns_use_jsonb() -> None:
    assert isinstance(AuditOutbox.__table__.c.old_values.type, JSONB)
    assert isinstance(AuditOutbox.__table__.c.new_values.type, JSONB)
