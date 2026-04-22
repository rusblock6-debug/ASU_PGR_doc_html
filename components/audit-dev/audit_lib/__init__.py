"""audit-lib: SQLAlchemy audit logging outbox library."""

from importlib.metadata import version as _pkg_version

__version__ = _pkg_version("audit-lib")

from audit_lib.config import configure_audit, setup
from audit_lib.context import (
    get_audit_service,
    get_audit_user,
    set_audit_context,
    set_audit_user,
)
from audit_lib.mixin import AuditMixin
from audit_lib.models import create_audit_model
from audit_lib.serializers import default_serializer
from audit_lib.table import create_audit_table, create_audit_table_async

__all__ = [
    "AuditMixin",
    "configure_audit",
    "create_audit_model",
    "create_audit_table",
    "create_audit_table_async",
    "default_serializer",
    "get_audit_service",
    "get_audit_user",
    "set_audit_context",
    "set_audit_user",
    "setup",
]
