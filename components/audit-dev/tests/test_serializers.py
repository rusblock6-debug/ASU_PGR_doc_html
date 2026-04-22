"""Tests for the default serializer (US-004)."""

from __future__ import annotations

import base64
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from audit_lib.config import configure_audit, reset_config
from audit_lib.mixin import AuditMixin
from audit_lib.models import create_audit_model
from audit_lib.serializers import default_serializer
from tests.conftest import PG_SYNC_URL

# ── Unit tests ───────────────────────────────────────────────────────────


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class IntColor(Enum):
    R = 1
    G = 2
    B = 3


class TestDefaultSerializerDatetime:
    def test_datetime_naive(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert default_serializer(dt) == "2024-01-15T10:30:00"

    def test_datetime_with_tz(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = default_serializer(dt)
        assert "2024-01-15T10:30:00" in result
        assert "+00:00" in result

    def test_date(self) -> None:
        d = date(2024, 6, 1)
        assert default_serializer(d) == "2024-06-01"

    def test_time_plain(self) -> None:
        t = time(14, 30, 0)
        assert default_serializer(t) == "14:30:00"

    def test_time_with_microseconds(self) -> None:
        t = time(14, 30, 0, 123456)
        assert default_serializer(t) == "14:30:00.123456"


class TestDefaultSerializerUUID:
    def test_uuid(self) -> None:
        uid = UUID("12345678-1234-5678-1234-567812345678")
        result = default_serializer(uid)
        assert result == "12345678-1234-5678-1234-567812345678"
        assert isinstance(result, str)

    def test_uuid4(self) -> None:
        uid = uuid4()
        result = default_serializer(uid)
        assert result == str(uid)


class TestDefaultSerializerDecimal:
    def test_decimal(self) -> None:
        d = Decimal("123.45")
        result = default_serializer(d)
        assert result == "123.45"
        assert isinstance(result, str)

    def test_decimal_integer(self) -> None:
        d = Decimal("100")
        assert default_serializer(d) == "100"

    def test_decimal_large(self) -> None:
        d = Decimal("999999999999999.999999")
        assert default_serializer(d) == "999999999999999.999999"


class TestDefaultSerializerEnum:
    def test_string_enum(self) -> None:
        assert default_serializer(Color.RED) == "red"

    def test_int_enum(self) -> None:
        assert default_serializer(IntColor.R) == 1


class TestDefaultSerializerCollections:
    def test_set(self) -> None:
        result = default_serializer({1, 2, 3})
        assert isinstance(result, list)
        assert sorted(result) == [1, 2, 3]

    def test_frozenset(self) -> None:
        result = default_serializer(frozenset(["a", "b"]))
        assert isinstance(result, list)
        assert sorted(result) == ["a", "b"]

    def test_empty_set(self) -> None:
        assert default_serializer(set()) == []

    def test_empty_frozenset(self) -> None:
        assert default_serializer(frozenset()) == []


class TestDefaultSerializerBytes:
    def test_bytes(self) -> None:
        data = b"hello world"
        result = default_serializer(data)
        assert result == base64.b64encode(data).decode("ascii")
        assert isinstance(result, str)

    def test_empty_bytes(self) -> None:
        result = default_serializer(b"")
        assert result == ""

    def test_binary_bytes(self) -> None:
        data = bytes(range(256))
        result = default_serializer(data)
        assert base64.b64decode(result) == data


class TestDefaultSerializerPydantic:
    def test_model_dump_duck_typing(self) -> None:
        """Objects with model_dump() are serialized via model_dump(mode='json')."""

        class FakeModel:
            def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
                if mode == "json":
                    return {"name": "Alice", "age": 30}
                return {"name": "Alice", "age": 30}

        result = default_serializer(FakeModel())
        assert result == {"name": "Alice", "age": 30}

    def test_model_dump_mode_json_is_used(self) -> None:
        """Verify that mode='json' is passed to model_dump."""

        class StrictModel:
            def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
                if mode == "json":
                    return {"dt": "2024-01-01T00:00:00"}
                return {"dt": datetime(2024, 1, 1)}

        result = default_serializer(StrictModel())
        assert result == {"dt": "2024-01-01T00:00:00"}


class TestDefaultSerializerPassthrough:
    """str, int, float, bool, None, list, dict pass through unchanged."""

    def test_str(self) -> None:
        assert default_serializer("hello") == "hello"

    def test_int(self) -> None:
        assert default_serializer(42) == 42

    def test_float(self) -> None:
        assert default_serializer(3.14) == 3.14

    def test_bool_true(self) -> None:
        assert default_serializer(True) is True

    def test_bool_false(self) -> None:
        assert default_serializer(False) is False

    def test_none(self) -> None:
        assert default_serializer(None) is None

    def test_list(self) -> None:
        lst = [1, 2, 3]
        assert default_serializer(lst) is lst

    def test_dict(self) -> None:
        d = {"key": "value"}
        assert default_serializer(d) is d


class TestDefaultSerializerUnknownTypes:
    """Unknown types pass through without error."""

    def test_custom_object(self) -> None:
        class Custom:
            pass

        obj = Custom()
        assert default_serializer(obj) is obj

    def test_complex_number(self) -> None:
        c = 1 + 2j
        assert default_serializer(c) == c

    def test_range(self) -> None:
        r = range(10)
        assert default_serializer(r) is r


# ── Integration test: CRUD with non-standard types ───────────────────────


class IntBase(DeclarativeBase):
    pass


IntAuditOutbox = create_audit_model(IntBase)


class TypedEntity(IntBase, AuditMixin):
    """Model with columns that return non-standard Python types."""

    __tablename__ = "typed_entities"

    id: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    uid: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )


@pytest.fixture(autouse=True)
def _configure_int() -> Generator[None]:
    reset_config()
    configure_audit(IntBase)
    yield
    reset_config()


@pytest.fixture()
def int_engine() -> Generator[sa.Engine]:
    eng = sa.create_engine(PG_SYNC_URL)
    IntBase.metadata.drop_all(eng)
    IntBase.metadata.create_all(eng)
    try:
        yield eng
    finally:
        IntBase.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture()
def int_session(int_engine: sa.Engine) -> Generator[Session]:
    with Session(int_engine) as sess:
        yield sess


def _int_outbox_records(session: Session) -> list[Any]:
    return list(session.execute(sa.select(IntAuditOutbox)).scalars())


class TestIntegrationNonStandardTypes:
    """Integration: CRUD with non-standard types saved through the serializer.

    Uses a model with UUID, Decimal, and DateTime columns — types that
    are NOT natively JSON-serializable.  Without the default serializer
    these operations would raise ``TypeError``.
    """

    def test_create_with_nonstandard_types(self, int_session: Session) -> None:
        """INSERT with datetime, UUID, Decimal values is stored without TypeError."""
        uid = uuid4()
        dt = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)

        entity = TypedEntity(
            name="test",
            uid=uid,
            amount=Decimal("99.99"),
            created_at=dt,
        )
        int_session.add(entity)
        int_session.commit()

        records = _int_outbox_records(int_session)
        assert len(records) == 1
        rec = records[0]
        assert rec.operation == "create"
        assert rec.new_values is not None
        assert rec.new_values["name"] == "test"
        # UUID serialized to string
        assert rec.new_values["uid"] == str(uid)
        # Decimal serialized to string
        assert rec.new_values["amount"] == "99.99"
        # datetime serialized to ISO 8601
        assert "2024-03-15" in rec.new_values["created_at"]

    def test_update_with_nonstandard_types(self, int_session: Session) -> None:
        """UPDATE with non-standard type values is stored without TypeError."""
        entity = TypedEntity(
            name="original",
            uid=uuid4(),
            amount=Decimal("10.00"),
            created_at=datetime.now(UTC),
        )
        int_session.add(entity)
        int_session.commit()

        new_uid = uuid4()
        entity.uid = new_uid
        entity.amount = Decimal("20.00")
        int_session.commit()

        records = _int_outbox_records(int_session)
        update_recs = [r for r in records if r.operation == "update"]
        assert len(update_recs) == 1
        assert update_recs[0].new_values["uid"] == str(new_uid)
        assert update_recs[0].new_values["amount"] == "20.00"

    def test_delete_with_nonstandard_types(self, int_session: Session) -> None:
        """DELETE with non-standard type values is stored without TypeError."""
        uid = uuid4()
        entity = TypedEntity(
            name="to-delete",
            uid=uid,
            amount=Decimal("5.00"),
            created_at=datetime.now(UTC),
        )
        int_session.add(entity)
        int_session.commit()

        int_session.delete(entity)
        int_session.commit()

        records = _int_outbox_records(int_session)
        delete_recs = [r for r in records if r.operation == "delete"]
        assert len(delete_recs) == 1
        assert delete_recs[0].old_values is not None
        assert delete_recs[0].old_values["name"] == "to-delete"
        assert delete_recs[0].old_values["uid"] == str(uid)
        assert delete_recs[0].new_values is None

    def test_full_crud_with_serializer_no_typeerror(
        self, int_session: Session
    ) -> None:
        """Full create-update-delete cycle completes without TypeError."""
        entity = TypedEntity(
            name="lifecycle",
            uid=uuid4(),
            amount=Decimal("100.00"),
            created_at=datetime.now(UTC),
        )
        int_session.add(entity)
        int_session.commit()

        entity.amount = Decimal("200.00")
        int_session.commit()

        int_session.delete(entity)
        int_session.commit()

        records = _int_outbox_records(int_session)
        ops = [r.operation for r in records]
        assert "create" in ops
        assert "update" in ops
        assert "delete" in ops
