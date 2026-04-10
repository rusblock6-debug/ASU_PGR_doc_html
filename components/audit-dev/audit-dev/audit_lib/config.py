"""Library configuration and initialization API."""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import DeclarativeBase

from audit_lib.models import create_audit_model
from audit_lib.serializers import default_serializer

logger = logging.getLogger("audit_lib")
_configured: bool = False
_audit_outbox_cls: type[Any] | None = None
_default_service_name: str | None = None
_serializer: Callable[[Any], Any] | None = None


def _get_audit_outbox_cls() -> type[Any]:
    """Return the configured AuditOutbox class or raise."""
    if _audit_outbox_cls is None:
        msg = (
            "AuditOutbox class not configured. "
            "Call configure_audit(Base) or setup(...) at startup."
        )
        raise RuntimeError(msg)
    return _audit_outbox_cls


def _get_audit_outbox_table() -> Any:
    """Return the ``__table__`` of the configured AuditOutbox model."""
    return _get_audit_outbox_cls().__table__


def get_default_service_name() -> str | None:
    """Return the default service name set during configuration."""
    return _default_service_name


def get_serializer() -> Callable[[Any], Any] | None:
    """Return the active serializer (default or custom) set during configuration."""
    return _serializer


def _find_existing_outbox(base: type[DeclarativeBase]) -> type[Any] | None:
    """Find an existing AuditOutbox model on the base, if any."""
    # Walk the registry to find a class mapped to "audit_outbox".
    for mapper in base.registry.mappers:
        cls = mapper.class_
        tbl = getattr(cls, "__tablename__", None)
        if tbl == "audit_outbox":
            return cls
    return None


def configure_audit(
    base: type[DeclarativeBase],
    *,
    service_name: str | None = None,
    serializer: Callable[[Any], Any] | None = None,
) -> type[Any]:
    """Auto-discover AuditMixin models and configure the audit outbox.

    Creates the ``AuditOutbox`` model on the provided declarative *base*
    and registers it for use by the event listeners.

    When no *serializer* is provided, the built-in
    :func:`~audit_lib.serializers.default_serializer` is used automatically.
    It handles ``datetime``, ``date``, ``time``, ``UUID``, ``Decimal``,
    ``Enum``, ``set``, ``frozenset``, ``bytes``, and pydantic v2 models.
    If a custom *serializer* is supplied, it **fully replaces** the default
    (there is no fallback chain).

    Parameters
    ----------
    base:
        The SQLAlchemy ``DeclarativeBase`` subclass used by the application.
    service_name:
        Default ``service_name`` written to every outbox record when the
        context-var is not set.
    serializer:
        Optional callable used to serialise non-JSON-serialisable field
        values before they are stored in ``old_values`` / ``new_values``.
        When ``None`` (the default), the built-in ``default_serializer``
        is used.  Pass a custom callable to **fully replace** the default
        serializer.

    Returns
    -------
    The generated ``AuditOutbox`` model class.
    """
    global _configured, _audit_outbox_cls  # noqa: PLW0603
    global _default_service_name, _serializer  # noqa: PLW0603

    if _configured:
        warnings.warn(
            "configure_audit() has already been called. "
            "Duplicate invocation ignored to prevent duplicate listeners.",
            stacklevel=2,
        )
        assert _audit_outbox_cls is not None
        return _audit_outbox_cls

    # Reuse if create_audit_model was already called on this base.
    existing = _find_existing_outbox(base)
    outbox_cls = existing if existing is not None else create_audit_model(base)
    _audit_outbox_cls = outbox_cls
    _default_service_name = service_name
    _serializer = serializer if serializer is not None else default_serializer
    _configured = True
    return outbox_cls


def setup(
    base: type[DeclarativeBase],
    *,
    service_name: str | None = None,
    serializer: Callable[[Any], Any] | None = None,
) -> type[Any]:
    """Convenience alias for :func:`configure_audit`.

    Registers event listeners and returns the ``AuditOutbox`` model::

        from audit_lib import setup
        AuditOutbox = setup(Base, service_name="billing")
    """
    return configure_audit(
        base,
        service_name=service_name,
        serializer=serializer,
    )


def reset_config() -> None:
    """Reset all configuration state. **For testing only.**"""
    global _configured, _audit_outbox_cls  # noqa: PLW0603
    global _default_service_name, _serializer  # noqa: PLW0603
    _configured = False
    _audit_outbox_cls = None
    _default_service_name = None
    _serializer = None
