"""Tests for the public API of audit_lib.daemon."""

from __future__ import annotations


def test_import_outbox_daemon() -> None:
    from audit_lib.daemon import OutboxDaemon

    assert OutboxDaemon is not None


def test_import_stream_publisher() -> None:
    from audit_lib.daemon import StreamPublisher

    assert StreamPublisher is not None


def test_import_outbox_reader() -> None:
    from audit_lib.daemon import OutboxReader

    assert OutboxReader is not None


def test_all_public_classes_in_module() -> None:
    import audit_lib.daemon as daemon_mod

    assert hasattr(daemon_mod, "OutboxDaemon")
    assert hasattr(daemon_mod, "StreamPublisher")
    assert hasattr(daemon_mod, "OutboxReader")


def test_all_list_contents() -> None:
    import audit_lib.daemon as daemon_mod

    expected = {"OutboxDaemon", "StreamPublisher", "OutboxReader"}
    assert set(daemon_mod.__all__) == expected


def test_daemon_not_in_main_all() -> None:
    import audit_lib

    assert "daemon" not in audit_lib.__all__
    assert "OutboxDaemon" not in audit_lib.__all__
