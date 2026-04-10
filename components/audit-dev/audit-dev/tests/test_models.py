"""Tests for AuditOutbox model using PostgreSQL."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session

from audit_lib.models import create_audit_model
from tests.conftest import PG_SYNC_URL


class Base(DeclarativeBase):
    pass


AuditOutbox = create_audit_model(Base)


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


def test_create_audit_record(session: Session) -> None:
    """Creating a valid AuditOutbox record succeeds."""
    record = AuditOutbox(
        entity_type="User",
        entity_id="123",
        operation="update",
        new_values={"name": "John"},
    )
    session.add(record)
    session.commit()

    result = session.execute(sa.select(AuditOutbox)).scalar_one()
    assert result.entity_type == "User"
    assert result.entity_id == "123"
    assert result.operation == "update"
    assert result.new_values == {"name": "John"}
    assert result.old_values is None
    assert result.user_id is None
    assert result.service_name is None
    assert result.processed is False
    assert isinstance(result.id, uuid.UUID)
    assert result.id.version == 7


def test_create_with_all_fields(session: Session) -> None:
    """All fields can be set explicitly."""
    record = AuditOutbox(
        entity_type="Order",
        entity_id="456",
        operation="create",
        old_values=None,
        new_values={"total": 100},
        user_id="user-42",
        service_name="order-service",
        processed=False,
    )
    session.add(record)
    session.commit()

    result = session.execute(sa.select(AuditOutbox)).scalar_one()
    assert result.user_id == "user-42"
    assert result.service_name == "order-service"


def test_missing_entity_type_raises(session: Session) -> None:
    """AuditOutbox without entity_type raises IntegrityError."""
    record = AuditOutbox(
        entity_id="123",
        operation="update",
    )
    session.add(record)
    with pytest.raises(IntegrityError):
        session.commit()


def test_missing_entity_id_raises(session: Session) -> None:
    """AuditOutbox without entity_id raises IntegrityError."""
    record = AuditOutbox(
        entity_type="User",
        operation="update",
    )
    session.add(record)
    with pytest.raises(IntegrityError):
        session.commit()


def test_missing_operation_raises(session: Session) -> None:
    """AuditOutbox without operation raises IntegrityError."""
    record = AuditOutbox(
        entity_type="User",
        entity_id="123",
    )
    session.add(record)
    with pytest.raises(IntegrityError):
        session.commit()


def test_indexes_exist(engine: sa.engine.Engine) -> None:
    """Required indexes are created on the table."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes("audit_outbox")
    index_names = {idx["name"] for idx in indexes}

    assert "ix_audit_outbox_entity" in index_names
    assert "ix_audit_outbox_processed" in index_names
    assert "ix_audit_outbox_timestamp" in index_names


def test_entity_index_columns(engine: sa.engine.Engine) -> None:
    """Entity index covers (entity_type, entity_id)."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes("audit_outbox")
    entity_idx = next(i for i in indexes if i["name"] == "ix_audit_outbox_entity")
    assert entity_idx["column_names"] == ["entity_type", "entity_id"]


def test_uuid_primary_key_auto_generated(session: Session) -> None:
    """UUIDv7 primary key is auto-generated when not provided."""
    r1 = AuditOutbox(entity_type="A", entity_id="1", operation="create")
    r2 = AuditOutbox(entity_type="B", entity_id="2", operation="create")
    session.add_all([r1, r2])
    session.commit()

    assert isinstance(r1.id, uuid.UUID)
    assert isinstance(r2.id, uuid.UUID)
    assert r1.id.version == 7
    assert r2.id.version == 7
    assert r1.id != r2.id


def test_processed_defaults_to_false(session: Session) -> None:
    """Processed field defaults to False."""
    record = AuditOutbox(
        entity_type="User", entity_id="1", operation="create"
    )
    session.add(record)
    session.commit()

    result = session.execute(sa.select(AuditOutbox)).scalar_one()
    assert result.processed is False


def test_timestamp_auto_set(session: Session) -> None:
    """Timestamp is auto-set on creation (via server_default)."""
    record = AuditOutbox(
        entity_type="User", entity_id="1", operation="create"
    )
    session.add(record)
    session.commit()

    result = session.execute(sa.select(AuditOutbox)).scalar_one()
    assert result.timestamp is not None


def test_factory_with_different_base() -> None:
    """Factory works with a separate DeclarativeBase."""

    class OtherBase(DeclarativeBase):
        pass

    other_audit_outbox = create_audit_model(OtherBase)

    engine = sa.create_engine(PG_SYNC_URL)
    OtherBase.metadata.drop_all(engine)
    OtherBase.metadata.create_all(engine)

    try:
        with Session(engine) as sess:
            record = other_audit_outbox(
                entity_type="Item", entity_id="99", operation="delete"
            )
            sess.add(record)
            sess.commit()

            result = sess.execute(sa.select(other_audit_outbox)).scalar_one()
            assert result.entity_type == "Item"
    finally:
        OtherBase.metadata.drop_all(engine)
        engine.dispose()
