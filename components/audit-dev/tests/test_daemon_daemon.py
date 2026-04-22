"""Tests for OutboxDaemon (US-004, US-005)."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from audit_lib.daemon.daemon import OutboxDaemon


def _make_record(**overrides: object) -> SimpleNamespace:
    """Create a fake outbox record."""
    defaults = {
        "id": uuid.uuid4(),
        "entity_type": "Order",
        "entity_id": "order-1",
        "operation": "INSERT",
        "old_values": None,
        "new_values": {"total": 100},
        "user_id": "user-1",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "service_name": "billing",
        "processed": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class _AsyncCtx:
    """Minimal async context manager for mocking session.begin()."""

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture
def mock_session_factory() -> MagicMock:
    """Create a mock async sessionmaker."""
    session = AsyncMock()
    session.begin = MagicMock(return_value=_AsyncCtx())

    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = ctx

    factory._session = session
    return factory


def _make_daemon(
    session_factory: MagicMock,
    **overrides: object,
) -> OutboxDaemon:
    """Create an OutboxDaemon with mocked dependencies."""
    kwargs: dict[str, object] = {
        "session_factory": session_factory,
        "outbox_model": MagicMock(),
        "batch_size": 10,
        "poll_interval": 0.01,
        "max_backoff": 0.08,
    }
    kwargs.update(overrides)
    return OutboxDaemon(**kwargs)  # type: ignore[arg-type]


class TestOutboxDaemonConstructor:
    """Tests for OutboxDaemon initialization."""

    def test_stores_parameters(self, mock_session_factory: MagicMock) -> None:
        model = MagicMock()
        daemon = OutboxDaemon(
            session_factory=mock_session_factory,
            outbox_model=model,
            host="rmq.local",
            port=5553,
            username="user",
            password="pass",
            vhost="/test",
            stream_name="my-stream",
            batch_size=50,
            poll_interval=2.0,
            max_backoff=30.0,
        )
        assert daemon._batch_size == 50
        assert daemon._poll_interval == 2.0
        assert daemon._max_backoff == 30.0
        assert daemon._running is False
        assert daemon._publisher._host == "rmq.local"
        assert daemon._publisher._stream_name == "my-stream"

    def test_defaults(self, mock_session_factory: MagicMock) -> None:
        daemon = OutboxDaemon(
            session_factory=mock_session_factory,
            outbox_model=MagicMock(),
        )
        assert daemon._batch_size == 100
        assert daemon._poll_interval == 1.0
        assert daemon._max_backoff == 60.0
        assert daemon._retention_hours == 72
        assert daemon._cleanup_interval_hours == 1.0

    def test_retention_params(self, mock_session_factory: MagicMock) -> None:
        daemon = OutboxDaemon(
            session_factory=mock_session_factory,
            outbox_model=MagicMock(),
            retention_hours=24,
            cleanup_interval_hours=0.5,
        )
        assert daemon._retention_hours == 24
        assert daemon._cleanup_interval_hours == 0.5

    def test_retention_disabled(self, mock_session_factory: MagicMock) -> None:
        daemon = OutboxDaemon(
            session_factory=mock_session_factory,
            outbox_model=MagicMock(),
            retention_hours=None,
        )
        assert daemon._retention_hours is None


class TestOutboxDaemonStop:
    """Tests for the stop mechanism."""

    def test_stop_sets_running_false(
        self, mock_session_factory: MagicMock
    ) -> None:
        daemon = _make_daemon(mock_session_factory)
        daemon._running = True
        daemon.stop()
        assert daemon._running is False


class TestOutboxDaemonPollCycle:
    """Tests for the poll cycle logic."""

    @patch("audit_lib.daemon.daemon.serialize_outbox_record")
    async def test_empty_batch_sleeps(
        self,
        mock_serialize: MagicMock,
        mock_session_factory: MagicMock,
    ) -> None:
        daemon = _make_daemon(mock_session_factory)
        daemon._running = True

        with (
            patch.object(
                daemon._reader, "fetch_batch",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "audit_lib.daemon.daemon.asyncio.sleep",
                new=AsyncMock(),
            ) as mock_sleep,
        ):
            await daemon._poll_cycle()
            mock_sleep.assert_awaited_once_with(daemon._poll_interval)

        mock_serialize.assert_not_called()

    @patch("audit_lib.daemon.daemon.serialize_outbox_record")
    async def test_processes_batch(
        self,
        mock_serialize: MagicMock,
        mock_session_factory: MagicMock,
    ) -> None:
        records = [_make_record(), _make_record()]
        mock_serialize.side_effect = [b'{"a":1}', b'{"b":2}']
        daemon = _make_daemon(mock_session_factory)
        daemon._running = True

        with (
            patch.object(
                daemon._reader, "fetch_batch", new=AsyncMock(return_value=records)
            ),
            patch.object(
                daemon._reader, "mark_processed", new=AsyncMock()
            ) as mock_mark,
            patch.object(
                daemon._publisher, "publish", new=AsyncMock()
            ) as mock_publish,
            patch("audit_lib.daemon.daemon.asyncio.sleep", new=AsyncMock()),
        ):
            await daemon._poll_cycle()

            assert mock_publish.await_count == 2
            mock_mark.assert_awaited_once()
            marked_ids = mock_mark.call_args[0][1]
            assert set(marked_ids) == {r.id for r in records}


class TestOutboxDaemonRetry:
    """Tests for publish retry with exponential backoff."""

    async def test_retry_with_exponential_backoff(
        self,
        mock_session_factory: MagicMock,
    ) -> None:
        daemon = _make_daemon(mock_session_factory, max_backoff=60.0)
        daemon._running = True
        records = [_make_record()]

        # Fail twice, then succeed
        publish_mock = AsyncMock(
            side_effect=[RuntimeError("conn lost"), RuntimeError("conn lost"), None]
        )

        sleep_times: list[float] = []

        async def tracking_sleep(t: float) -> None:
            sleep_times.append(t)
            # don't actually sleep in tests

        with (
            patch.object(daemon._publisher, "publish", new=publish_mock),
            patch(
                "audit_lib.daemon.daemon.serialize_outbox_record",
                return_value=b"{}",
            ),
            patch(
                "audit_lib.daemon.daemon.asyncio.sleep",
                side_effect=tracking_sleep,
            ),
        ):
            await daemon._publish_with_retry(records)

        assert publish_mock.await_count == 3
        assert sleep_times == [1.0, 2.0]

    async def test_backoff_caps_at_max(
        self,
        mock_session_factory: MagicMock,
    ) -> None:
        daemon = _make_daemon(mock_session_factory, max_backoff=2.0)
        daemon._running = True
        records = [_make_record()]

        # Fail 4 times (backoff: 1, 2, 2, 2), then succeed
        publish_mock = AsyncMock(
            side_effect=[
                RuntimeError("e"),
                RuntimeError("e"),
                RuntimeError("e"),
                RuntimeError("e"),
                None,
            ]
        )

        sleep_times: list[float] = []

        async def tracking_sleep(t: float) -> None:
            sleep_times.append(t)

        with (
            patch.object(daemon._publisher, "publish", new=publish_mock),
            patch(
                "audit_lib.daemon.daemon.serialize_outbox_record",
                return_value=b"{}",
            ),
            patch(
                "audit_lib.daemon.daemon.asyncio.sleep",
                side_effect=tracking_sleep,
            ),
        ):
            await daemon._publish_with_retry(records)

        assert sleep_times == [1.0, 2.0, 2.0, 2.0]


class TestOutboxDaemonRun:
    """Tests for the main run loop."""

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_run_stops_gracefully(
        self,
        mock_producer_cls: MagicMock,
        mock_session_factory: MagicMock,
    ) -> None:
        mock_producer_cls.return_value = AsyncMock()

        daemon = _make_daemon(mock_session_factory)

        stop_effect = AsyncMock(side_effect=daemon.stop)
        with patch.object(daemon, "_poll_cycle", new=stop_effect):
            await daemon.run()

        assert daemon._running is False

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_run_processes_multiple_cycles(
        self,
        mock_producer_cls: MagicMock,
        mock_session_factory: MagicMock,
    ) -> None:
        mock_producer_cls.return_value = AsyncMock()
        daemon = _make_daemon(mock_session_factory)

        call_count = 0

        async def counting_cycle() -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                daemon.stop()

        with patch.object(daemon, "_poll_cycle", new=counting_cycle):
            await daemon.run()

        assert call_count == 3

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_run_starts_cleanup_task(
        self,
        mock_producer_cls: MagicMock,
        mock_session_factory: MagicMock,
    ) -> None:
        """Cleanup task is created when retention_hours is set."""
        mock_producer_cls.return_value = AsyncMock()
        daemon = _make_daemon(mock_session_factory, retention_hours=24)

        with (
            patch.object(
                daemon, "_poll_cycle",
                new=AsyncMock(side_effect=daemon.stop),
            ),
            patch.object(
                daemon, "_cleanup_loop", new=AsyncMock(),
            ),
            patch(
                "audit_lib.daemon.daemon.asyncio.create_task",
                wraps=asyncio.create_task,
            ) as mock_create_task,
        ):
            await daemon.run()
            mock_create_task.assert_called_once()

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_run_no_cleanup_task_when_retention_none(
        self,
        mock_producer_cls: MagicMock,
        mock_session_factory: MagicMock,
    ) -> None:
        """Cleanup task is NOT created when retention_hours is None."""
        mock_producer_cls.return_value = AsyncMock()
        daemon = _make_daemon(mock_session_factory, retention_hours=None)

        with (
            patch.object(
                daemon, "_poll_cycle",
                new=AsyncMock(side_effect=daemon.stop),
            ),
            patch(
                "audit_lib.daemon.daemon.asyncio.create_task",
                wraps=asyncio.create_task,
            ) as mock_create_task,
        ):
            await daemon.run()
            mock_create_task.assert_not_called()


class TestOutboxDaemonCleanupLoop:
    """Tests for the cleanup loop (US-005)."""

    async def test_cleanup_loop_calls_reader(
        self,
        mock_session_factory: MagicMock,
    ) -> None:
        """Cleanup loop calls reader.cleanup_old_records."""
        daemon = _make_daemon(
            mock_session_factory,
            retention_hours=48,
            cleanup_interval_hours=0.001,  # ~3.6 seconds
        )
        daemon._running = True

        cleanup_called = asyncio.Event()

        async def fake_cleanup(*args: object, **kwargs: object) -> int:
            cleanup_called.set()
            daemon._running = False
            return 5

        with (
            patch.object(
                daemon._reader, "cleanup_old_records", new=fake_cleanup
            ),
            patch(
                "audit_lib.daemon.daemon.asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            await daemon._cleanup_loop()

        assert cleanup_called.is_set()

    async def test_cleanup_loop_survives_errors(
        self,
        mock_session_factory: MagicMock,
    ) -> None:
        """Cleanup loop continues after errors."""
        daemon = _make_daemon(
            mock_session_factory,
            retention_hours=48,
            cleanup_interval_hours=0.001,
        )
        daemon._running = True
        call_count = 0

        original_session_factory_call = mock_session_factory.return_value

        def session_factory_side_effect() -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call raises an error
                ctx = AsyncMock()
                ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
                ctx.__aexit__ = AsyncMock(return_value=False)
                return ctx
            # Second call: stop the loop
            daemon._running = False
            return original_session_factory_call

        mock_session_factory.side_effect = session_factory_side_effect

        with patch(
            "audit_lib.daemon.daemon.asyncio.sleep",
            new=AsyncMock(),
        ):
            await daemon._cleanup_loop()

        # Should have called the factory at least twice (error + stop)
        assert call_count >= 2
