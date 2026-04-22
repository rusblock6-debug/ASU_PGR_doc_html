"""AuditMixin — automatic audit trail via SQLAlchemy mapper events (sync)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, UOWTransaction

from audit_lib.context import get_audit_service, get_audit_user
from audit_lib.ids import generate_uuid7

_flush_listener_installed: bool = False


def _ensure_flush_listener() -> None:
    """Install the ``before_flush`` listener on Session (once globally)."""
    global _flush_listener_installed  # noqa: PLW0603
    if _flush_listener_installed:
        return
    event.listen(Session, "before_flush", _before_flush_load_expired)
    _flush_listener_installed = True


class AuditMixin:
    """Mixin that hooks SQLAlchemy mapper events to write audit outbox records.

    Usage::

        class User(Base, AuditMixin):
            __tablename__ = "users"
            id = mapped_column(Integer, primary_key=True)
            name = mapped_column(String)

    By default all columns are audited. To exclude columns, set
    ``__audit_exclude__`` on the model class::

        class User(Base, AuditMixin):
            __audit_exclude__ = {"password_hash"}
    """

    __audit_exclude__: ClassVar[set[str]] = set()

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "__tablename__"):
            event.listen(cls, "after_insert", _after_insert)
            event.listen(cls, "after_update", _after_update)
            event.listen(cls, "after_delete", _after_delete)
            _ensure_flush_listener()


def _reset_flush_listener() -> None:
    """Remove the before_flush listener. **For testing only.**"""
    global _flush_listener_installed  # noqa: PLW0603
    if _flush_listener_installed:
        event.remove(Session, "before_flush", _before_flush_load_expired)
        _flush_listener_installed = False


def _get_entity_id(instance: Any) -> str:
    """Return the primary key value(s) of *instance* as a string."""
    mapper = inspect(type(instance))
    pk_cols = mapper.primary_key
    pk_vals = [getattr(instance, col.key) for col in pk_cols]
    if len(pk_vals) == 1:
        return str(pk_vals[0])
    return str(tuple(pk_vals))


def _auditable_columns(instance: Any) -> list[str]:
    """Return column attribute names that should be audited."""
    mapper = inspect(type(instance))
    exclude: set[str] = getattr(instance.__class__, "__audit_exclude__", set())
    return [attr.key for attr in mapper.column_attrs if attr.key not in exclude]


def _snapshot(instance: Any, columns: list[str]) -> dict[str, Any]:
    """Return a dict of {column: value} for the given columns."""
    result: dict[str, Any] = {}
    for col in columns:
        val = getattr(instance, col)
        result[col] = val
    return result


def _serialize_value(val: Any) -> Any:
    """Serialize a value using the custom serializer if configured."""
    from audit_lib.config import get_serializer

    serializer = get_serializer()
    if serializer is not None:
        return serializer(val)
    return val


def _serialize_dict(d: dict[str, Any] | None) -> dict[str, Any] | None:
    """Apply the custom serializer to every value in a dict."""
    if d is None:
        return None
    return {k: _serialize_value(v) for k, v in d.items()}


def _insert_outbox(
    connection: Any,
    instance: Any,
    operation: str,
    old_values: dict[str, Any] | None,
    new_values: dict[str, Any] | None,
) -> None:
    """Insert an AuditOutbox record via the connection (safe during flush)."""
    from audit_lib.config import _get_audit_outbox_table, get_default_service_name

    audit_table = _get_audit_outbox_table()
    service = get_audit_service() or get_default_service_name()
    connection.execute(
        audit_table.insert().values(
            id=generate_uuid7(),
            entity_type=instance.__class__.__tablename__,
            entity_id=_get_entity_id(instance),
            operation=operation,
            old_values=_serialize_dict(old_values),
            new_values=_serialize_dict(new_values),
            user_id=get_audit_user(),
            service_name=service,
            timestamp=datetime.now(UTC),
            processed=False,
        )
    )


def _before_flush_load_expired(
    session: Session,
    flush_context: UOWTransaction,
    instances: Any,
) -> None:
    """Force-load expired attributes on dirty AuditMixin instances.

    When an attribute is expired (e.g. after commit) and then set to a new
    value without being read first, SQLAlchemy records the change in
    ``history.added`` but ``history.deleted`` is empty because the old value
    was never loaded.  We fix this by saving/restoring the pending values
    around a refresh so that the old values appear in ``history.deleted``.
    """
    for instance in list(session.dirty):
        if not isinstance(instance, AuditMixin):
            continue
        if not session.is_modified(instance, include_collections=False):
            continue

        insp = inspect(instance)
        assert insp is not None
        # Identify columns whose old value was never loaded (expired).
        pending: dict[str, Any] = {}
        columns = _auditable_columns(instance)
        for col in columns:
            hist = insp.attrs[col].history
            if hist.added and not hist.deleted:
                # Save the pending new value.
                pending[col] = hist.added[0]

        if pending:
            # Refresh the expired columns from the DB (loads old values).
            session.refresh(instance, list(pending.keys()))
            # Re-apply the pending changes so history now has old in deleted.
            for col, val in pending.items():
                setattr(instance, col, val)


def _after_insert(mapper: Any, connection: Any, target: Any) -> None:
    """after_insert event: record a 'create' audit entry."""
    columns = _auditable_columns(target)
    new_values = _snapshot(target, columns)
    _insert_outbox(connection, target, "create", None, new_values)


def _after_update(mapper: Any, connection: Any, target: Any) -> None:
    """after_update event: record an 'update' audit entry (only changed fields)."""
    columns = _auditable_columns(target)
    insp = inspect(target)

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    for col in columns:
        hist = insp.attrs[col].history
        if hist.has_changes():
            if hist.deleted:
                old_values[col] = hist.deleted[0]
            if hist.added:
                new_values[col] = hist.added[0]

    # If nothing actually changed, skip creating an outbox record.
    if not old_values and not new_values:
        return

    _insert_outbox(connection, target, "update", old_values, new_values)


def _after_delete(mapper: Any, connection: Any, target: Any) -> None:
    """after_delete event: record a 'delete' audit entry."""
    columns = _auditable_columns(target)
    old_values = _snapshot(target, columns)
    _insert_outbox(connection, target, "delete", old_values, None)
