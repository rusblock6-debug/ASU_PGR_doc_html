"""Daemon module for publishing outbox records to RabbitMQ Stream.

This is an optional module that requires the ``rstream`` package.
Install with::

    pip install audit-lib[daemon]
"""

try:
    import rstream as _rstream  # noqa: F401
except ImportError as _exc:
    raise ImportError(
        "Install audit-lib[daemon] to use the daemon module"
    ) from _exc

from audit_lib.daemon.daemon import OutboxDaemon
from audit_lib.daemon.publisher import StreamPublisher
from audit_lib.daemon.reader import OutboxReader

__all__ = [
    "OutboxDaemon",
    "OutboxReader",
    "StreamPublisher",
]
