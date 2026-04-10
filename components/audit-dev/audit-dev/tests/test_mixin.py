"""Tests for AuditMixin with sync SQLAlchemy sessions and PostgreSQL."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any, ClassVar

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from audit_lib.config import configure_audit, reset_config
from audit_lib.context import set_audit_context
from audit_lib.mixin import AuditMixin
from audit_lib.models import create_audit_model
from tests.conftest import PG_SYNC_URL

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


class SecretEntity(Base, AuditMixin):
    """Model where ALL non-PK columns are excluded from audit."""

    __tablename__ = "secret_entities"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    secret: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    token: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    __audit_exclude__: ClassVar[set[str]] = {"id", "secret", "token"}


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _configure_audit() -> Generator[None]:
    """Ensure AuditOutbox is configured for the mixin."""
    reset_config()
    configure_audit(Base)
    yield
    reset_config()


@pytest.fixture()
def engine() -> Generator[sa.engine.Engine]:
    eng = sa.create_engine(PG_SYNC_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def session(engine: sa.engine.Engine) -> Generator[Session]:
    with Session(engine) as sess:
        yield sess


# ── Helpers ──────────────────────────────────────────────────────────────


def _outbox_records(session: Session) -> list[Any]:
    return list(session.execute(sa.select(AuditOutbox)).scalars())


# ── INSERT tests ─────────────────────────────────────────────────────────


def test_insert_creates_audit_record(session: Session) -> None:
    """INSERT on a mixin model creates an outbox record with operation='create'."""
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "create"
    assert rec.entity_type == "users"
    assert rec.entity_id == str(user.id)
    assert rec.old_values is None
    assert rec.new_values is not None
    assert rec.new_values["name"] == "Alice"
    assert rec.new_values["email"] == "alice@example.com"
    assert isinstance(rec.id, uuid.UUID)
    assert rec.id.version == 7


def test_insert_new_values_contain_all_auditable_fields(session: Session) -> None:
    """new_values on INSERT contains all non-excluded columns."""
    user = User(name="Alice")
    session.add(user)
    session.commit()

    rec = _outbox_records(session)[0]
    assert "name" in rec.new_values
    assert "email" in rec.new_values
    assert "id" in rec.new_values


# ── UPDATE tests ─────────────────────────────────────────────────────────


def test_update_creates_audit_record(session: Session) -> None:
    """UPDATE creates an outbox record with old/new values for changed fields."""
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()

    # Clear outbox from INSERT
    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    user.name = "Bob"
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "update"
    assert rec.old_values == {"name": "Alice"}
    assert rec.new_values == {"name": "Bob"}


def test_update_multiple_fields(session: Session) -> None:
    """UPDATE with multiple changed fields captures all of them."""
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()

    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    user.name = "Bob"
    user.email = "bob@example.com"
    session.commit()

    rec = _outbox_records(session)[0]
    assert rec.old_values == {"name": "Alice", "email": "alice@example.com"}
    assert rec.new_values == {"name": "Bob", "email": "bob@example.com"}


# ── DELETE tests ─────────────────────────────────────────────────────────


def test_delete_creates_audit_record(session: Session) -> None:
    """DELETE creates an outbox record with old_values and new_values=None."""
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()
    user_id = user.id

    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    session.delete(user)
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "delete"
    assert rec.entity_id == str(user_id)
    assert rec.new_values is None
    assert rec.old_values is not None
    assert rec.old_values["name"] == "Alice"
    assert rec.old_values["email"] == "alice@example.com"


# ── Context integration ─────────────────────────────────────────────────


def test_user_id_from_context(session: Session) -> None:
    """user_id is read from contextvars via get_audit_user()."""
    with set_audit_context(user_id="user-42", service_name="billing"):
        user = User(name="Alice")
        session.add(user)
        session.commit()

    rec = _outbox_records(session)[0]
    assert rec.user_id == "user-42"
    assert rec.service_name == "billing"


def test_no_context_yields_none(session: Session) -> None:
    """Without context, user_id and service_name are None."""
    user = User(name="Alice")
    session.add(user)
    session.commit()

    rec = _outbox_records(session)[0]
    assert rec.user_id is None
    assert rec.service_name is None


# ── Negative cases ───────────────────────────────────────────────────────


def test_excluded_field_not_in_audit(session: Session) -> None:
    """Fields listed in __audit_exclude__ are NOT present in old_values/new_values."""
    user = User(name="Alice", password_hash="secret123")
    session.add(user)
    session.commit()

    rec = _outbox_records(session)[0]
    assert "password_hash" not in rec.new_values


def test_excluded_field_not_in_update_audit(session: Session) -> None:
    """Excluded fields are not tracked on UPDATE even if changed."""
    user = User(name="Alice", password_hash="old_hash")
    session.add(user)
    session.commit()

    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    user.password_hash = "new_hash"
    session.commit()

    # password_hash is excluded, so no audit record if only excluded fields changed
    records = _outbox_records(session)
    assert len(records) == 0


def test_excluded_field_not_in_mixed_update(session: Session) -> None:
    """Updating both excluded and non-excluded fields only audits non-excluded."""
    user = User(name="Alice", password_hash="old_hash")
    session.add(user)
    session.commit()

    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    user.name = "Bob"
    user.password_hash = "new_hash"
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "update"
    assert "name" in rec.new_values
    assert rec.new_values["name"] == "Bob"
    assert "password_hash" not in rec.new_values
    assert "password_hash" not in rec.old_values


def test_no_change_no_audit_on_update(session: Session) -> None:
    """If no auditable fields actually changed on flush, no outbox record is created."""
    user = User(name="Alice")
    session.add(user)
    session.commit()

    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    # Re-set same value — SQLAlchemy may or may not detect as "change"
    # depending on the attribute. But flush with no net change should yield no record.
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 0


def test_excluded_field_not_in_delete_audit(session: Session) -> None:
    """Excluded fields are not present in delete old_values."""
    user = User(name="Alice", password_hash="secret123")
    session.add(user)
    session.commit()

    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    session.delete(user)
    session.commit()

    rec = _outbox_records(session)[0]
    assert "password_hash" not in rec.old_values


# ── Same-session (same transaction) test ─────────────────────────────────


def test_audit_record_in_same_transaction(engine: sa.engine.Engine) -> None:
    """AuditOutbox record is added to the SAME session (same transaction)."""
    with Session(engine) as session:
        user = User(name="Alice")
        session.add(user)
        session.flush()

        # After flush, the record is persisted but in the same transaction.
        # We can query it.
        records = list(session.execute(sa.select(AuditOutbox)).scalars())
        assert len(records) == 1
        assert records[0].operation == "create"

        session.rollback()

    # After rollback, nothing should be persisted
    with Session(engine) as session:
        records = list(session.execute(sa.select(AuditOutbox)).scalars())
        assert len(records) == 0


# ── All-fields-excluded tests ────────────────────────────────────────────


def test_all_excluded_insert_creates_record_with_empty_diffs(
    session: Session,
) -> None:
    """INSERT on a model with all fields excluded still creates an outbox record."""
    entity = SecretEntity(secret="s3cret", token="tok123")
    session.add(entity)
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "create"
    assert rec.new_values == {}
    assert rec.old_values is None


def test_all_excluded_delete_creates_record_with_empty_diffs(
    session: Session,
) -> None:
    """DELETE on a model with all fields excluded still creates an outbox record."""
    entity = SecretEntity(secret="s3cret", token="tok123")
    session.add(entity)
    session.commit()

    for r in _outbox_records(session):
        session.delete(r)
    session.commit()

    session.delete(entity)
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1
    rec = records[0]
    assert rec.operation == "delete"
    assert rec.old_values == {}
    assert rec.new_values is None
