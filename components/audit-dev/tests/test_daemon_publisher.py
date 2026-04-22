"""Tests for StreamPublisher (US-001)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from audit_lib.daemon.publisher import StreamPublisher


@pytest.fixture
def mock_producer() -> AsyncMock:
    """Create a mock rstream Producer."""
    producer = AsyncMock()
    producer.start = AsyncMock()
    producer.create_stream = AsyncMock()
    producer.send = AsyncMock()
    producer.close = AsyncMock()
    return producer


class TestStreamPublisher:
    """Unit tests for StreamPublisher."""

    def test_constructor_stores_parameters(self) -> None:
        pub = StreamPublisher(
            host="rmq.local",
            port=5553,
            username="user",
            password="pass",
            vhost="/test",
            stream_name="my-stream",
        )
        assert pub._host == "rmq.local"
        assert pub._port == 5553
        assert pub._username == "user"
        assert pub._password == "pass"
        assert pub._vhost == "/test"
        assert pub._stream_name == "my-stream"

    def test_constructor_defaults(self) -> None:
        pub = StreamPublisher()
        assert pub._host == "localhost"
        assert pub._port == 5552
        assert pub._username == "guest"
        assert pub._password == "guest"
        assert pub._vhost == "/"
        assert pub._stream_name == "audit-events"
        assert pub._producer is None

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_connect_creates_producer(
        self, mock_cls: MagicMock
    ) -> None:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        pub = StreamPublisher(host="rmq", stream_name="test-stream")
        await pub.connect()

        mock_cls.assert_called_once_with(
            host="rmq",
            port=5552,
            username="guest",
            password="guest",
            vhost="/",
        )
        mock_instance.start.assert_awaited_once()
        mock_instance.create_stream.assert_awaited_once_with(
            "test-stream", exists_ok=True
        )
        assert pub._producer is mock_instance

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_publish_sends_message(self, mock_cls: MagicMock) -> None:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        pub = StreamPublisher(stream_name="events")
        await pub.connect()
        await pub.publish(b'{"event": "test"}')

        mock_instance.send.assert_awaited_once_with(
            stream="events",
            message=b'{"event": "test"}',
        )

    async def test_publish_without_connect_raises(self) -> None:
        pub = StreamPublisher()
        with pytest.raises(RuntimeError, match="not connected"):
            await pub.publish(b"hello")

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_close_shuts_down_producer(
        self, mock_cls: MagicMock
    ) -> None:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        pub = StreamPublisher()
        await pub.connect()
        await pub.close()

        mock_instance.close.assert_awaited_once()
        assert pub._producer is None

    async def test_close_without_connect_is_noop(self) -> None:
        pub = StreamPublisher()
        await pub.close()  # should not raise

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_context_manager(self, mock_cls: MagicMock) -> None:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        async with StreamPublisher(stream_name="ctx-stream") as pub:
            assert pub._producer is mock_instance
            mock_instance.start.assert_awaited_once()

        mock_instance.close.assert_awaited_once()

    @patch("audit_lib.daemon.publisher.Producer")
    async def test_context_manager_closes_on_error(
        self, mock_cls: MagicMock
    ) -> None:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        with pytest.raises(ValueError, match="boom"):
            async with StreamPublisher() as _pub:
                raise ValueError("boom")

        mock_instance.close.assert_awaited_once()
