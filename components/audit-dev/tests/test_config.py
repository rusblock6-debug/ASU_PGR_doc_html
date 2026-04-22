"""Tests for library configuration and initialization API (US-007)."""

from __future__ import annotations

import warnings
from collections.abc import Generator
from datetime import date
from typing import Any, ClassVar

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from audit_lib import (
    AuditMixin,
    configure_audit,
    create_audit_model,
    set_audit_context,
    setup,
)
from audit_lib.config import reset_config
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
    created: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    __audit_exclude__: ClassVar[set[str]] = set()


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset() -> Generator[None]:
    """Reset config before and after each test."""
    reset_config()
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


# ── configure_audit tests ───────────────────────────────────────────────


def test_configure_audit_returns_outbox_class() -> None:
    """configure_audit(Base) returns the AuditOutbox model class."""
    outbox = configure_audit(Base)
    assert hasattr(outbox, "__tablename__")
    assert outbox.__tablename__ == "audit_outbox"


def test_configure_audit_twice_warns(session: Session) -> None:
    """Calling configure_audit twice warns, no duplicate listeners."""
    configure_audit(Base)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        configure_audit(Base)
        assert len(w) == 1
        assert "already been called" in str(w[0].message)

    # Still works — should produce exactly one audit record, not two.
    user = User(name="Alice")
    session.add(user)
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1


def test_setup_is_alias_for_configure_audit() -> None:
    """setup() works identically to configure_audit()."""
    outbox = setup(Base)
    assert outbox.__tablename__ == "audit_outbox"

    # Second call via configure_audit should warn (already configured)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        configure_audit(Base)
        assert len(w) == 1


# ── Default service_name ────────────────────────────────────────────────


def test_default_service_name(session: Session) -> None:
    """service_name option sets the default when context var is not set."""
    configure_audit(Base, service_name="my-service")

    user = User(name="Alice")
    session.add(user)
    session.commit()

    rec = _outbox_records(session)[0]
    assert rec.service_name == "my-service"


def test_context_service_overrides_default(session: Session) -> None:
    """Context-var service_name overrides the configured default."""
    configure_audit(Base, service_name="default-svc")

    with set_audit_context(service_name="override-svc"):
        user = User(name="Alice")
        session.add(user)
        session.commit()

    rec = _outbox_records(session)[0]
    assert rec.service_name == "override-svc"


# ── Custom serializer ──────────────────────────────────────────────────


def test_custom_serializer_applied(session: Session) -> None:
    """Custom serializer transforms values in old_values/new_values."""

    def custom_ser(val: Any) -> Any:
        if isinstance(val, date):
            return val.isoformat()
        return val

    configure_audit(Base, serializer=custom_ser)

    user = User(name="Alice", created=date(2024, 1, 15))
    session.add(user)
    session.commit()

    rec = _outbox_records(session)[0]
    assert rec.new_values["created"] == "2024-01-15"
    assert rec.new_values["name"] == "Alice"  # non-date values pass through


# ── Public API exports ─────────────────────────────────────────────────


def test_public_api_exports() -> None:
    """All documented public names are importable from audit_lib."""
    import audit_lib

    expected = {
        "AuditMixin",
        "configure_audit",
        "create_audit_model",
        "get_audit_service",
        "get_audit_user",
        "set_audit_context",
        "set_audit_user",
        "setup",
    }
    assert expected.issubset(set(audit_lib.__all__))


def test_example_usage(session: Session) -> None:
    """Example from AC: configure_audit(Base) from audit_lib."""
    configure_audit(Base)

    user = User(name="ExampleUser")
    session.add(user)
    session.commit()

    records = _outbox_records(session)
    assert len(records) == 1
    assert records[0].new_values["name"] == "ExampleUser"
