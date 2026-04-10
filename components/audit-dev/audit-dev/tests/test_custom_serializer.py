"""Tests for custom serializer replacement (US-005)."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from audit_lib.config import configure_audit, get_serializer, reset_config
from audit_lib.mixin import AuditMixin, _serialize_dict
from audit_lib.models import create_audit_model
from tests.conftest import PG_SYNC_URL

# ── Separate DeclarativeBase to avoid table collisions ────────────────────


class CustBase(DeclarativeBase):
    pass


CustAuditOutbox = create_audit_model(CustBase)


class CustEntity(CustBase, AuditMixin):
    """Model with non-standard-type columns for custom serializer tests."""

    __tablename__ = "cust_entities"

    id: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    uid: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )


@pytest.fixture()
def cust_engine() -> Generator[sa.Engine]:
    eng = sa.create_engine(PG_SYNC_URL)
    CustBase.metadata.drop_all(eng)
    CustBase.metadata.create_all(eng)
    try:
        yield eng
    finally:
        CustBase.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def cust_session(cust_engine: sa.Engine) -> Generator[Session]:
    with Session(cust_engine) as sess:
        yield sess


def _cust_outbox_records(session: Session) -> list[Any]:
    return list(session.execute(sa.select(CustAuditOutbox)).scalars())


# ── Tests ─────────────────────────────────────────────────────────────────


class TestCustomSerializerReplacesDefault:
    """US-005: Custom serializer fully replaces the default."""

    def test_custom_serializer_replaces_default(self) -> None:
        """When serializer=custom_fn, get_serializer() returns custom_fn."""
        reset_config()

        def custom_fn(val: Any) -> Any:
            return val

        configure_audit(CustBase, serializer=custom_fn)
        try:
            assert get_serializer() is custom_fn
        finally:
            reset_config()

    def test_default_serializer_not_called_with_custom(self) -> None:
        """When serializer=custom_fn, default_serializer is NOT called.

        We verify by checking that the serialization output differs from
        what default_serializer would produce: str(datetime) uses a space
        separator while isoformat() uses 'T'.
        """
        reset_config()
        custom_calls: list[Any] = []

        def custom_fn(val: Any) -> Any:
            custom_calls.append(val)
            return str(val)

        configure_audit(CustBase, serializer=custom_fn)
        try:
            dt = datetime(2024, 1, 1, tzinfo=UTC)
            result = _serialize_dict({"dt": dt})

            # Custom serializer was called with the raw datetime
            assert len(custom_calls) == 1
            assert custom_calls[0] is dt

            # str(datetime) → "2024-01-01 00:00:00+00:00" (space)
            # isoformat()  → "2024-01-01T00:00:00+00:00" (T)
            # Result matches str(), proving default_serializer was NOT used
            assert result is not None
            assert result["dt"] == str(dt)
            assert "T" not in result["dt"]
        finally:
            reset_config()

    def test_custom_serializer_receives_raw_values(
        self, cust_session: Session
    ) -> None:
        """Custom serializer receives raw values, not pre-processed by default."""
        reset_config()
        received: list[tuple[type, Any]] = []

        def recording_serializer(val: Any) -> Any:
            received.append((type(val), val))
            # Must return JSON-serializable values for JSONB storage
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, Decimal):
                return str(val)
            if isinstance(val, uuid.UUID):
                return str(val)
            return val

        configure_audit(CustBase, serializer=recording_serializer)
        try:
            uid = uuid4()
            dt = datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)
            amount = Decimal("42.50")

            entity = CustEntity(
                name="raw-test",
                uid=uid,
                amount=amount,
                created_at=dt,
            )
            cust_session.add(entity)
            cust_session.commit()

            # The custom serializer received raw (non-pre-processed) values
            received_types = [t for t, _ in received]
            assert datetime in received_types
            assert uuid.UUID in received_types
            assert Decimal in received_types

            # Verify the exact raw objects were passed (identity check)
            received_vals = [v for _, v in received]
            assert dt in received_vals
            assert uid in received_vals
            assert amount in received_vals
        finally:
            reset_config()

    def test_datetime_passes_through_with_noop_serializer(self) -> None:
        """If custom serializer doesn't handle datetime, it passes through as-is.

        The user is responsible for their serializer — the library does NOT
        fall back to default_serializer for unhandled types.
        """
        reset_config()

        def noop_serializer(val: Any) -> Any:
            """Returns everything unchanged — deliberately skips datetime."""
            return val

        configure_audit(CustBase, serializer=noop_serializer)
        try:
            dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
            uid = uuid4()
            amount = Decimal("99.99")

            result = _serialize_dict({
                "name": "test",
                "uid": uid,
                "amount": amount,
                "created_at": dt,
            })

            assert result is not None
            # datetime remains as datetime object (not converted to ISO string)
            assert isinstance(result["created_at"], datetime)
            assert result["created_at"] is dt
            # UUID remains as UUID object
            assert isinstance(result["uid"], uuid.UUID)
            assert result["uid"] is uid
            # Decimal remains as Decimal object
            assert isinstance(result["amount"], Decimal)
            assert result["amount"] is amount
        finally:
            reset_config()
