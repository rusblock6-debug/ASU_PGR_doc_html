"""RabbitMQ Stream publisher using rstream."""

from __future__ import annotations

from types import TracebackType

from rstream import Producer


class StreamPublisher:
    """Publishes messages to a RabbitMQ Stream via ``rstream``.

    Parameters
    ----------
    host:
        RabbitMQ host.
    port:
        RabbitMQ Stream protocol port (default 5552).
    username:
        Authentication username.
    password:
        Authentication password.
    vhost:
        Virtual host (default ``/``).
    stream_name:
        Name of the target stream.
    """

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 5552,
        username: str = "guest",
        password: str = "guest",
        vhost: str = "/",
        stream_name: str = "audit-events",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._vhost = vhost
        self._stream_name = stream_name
        self._producer: Producer | None = None

    async def connect(self) -> None:
        """Establish connection and create an rstream producer."""
        self._producer = Producer(
            host=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            vhost=self._vhost,
        )
        await self._producer.start()
        await self._producer.create_stream(
            self._stream_name, exists_ok=True
        )

    async def publish(self, message: bytes) -> None:
        """Send a single message to the stream.

        Parameters
        ----------
        message:
            Raw bytes payload to publish.
        """
        if self._producer is None:
            msg = "StreamPublisher is not connected. Call connect() first."
            raise RuntimeError(msg)
        await self._producer.send(
            stream=self._stream_name,
            message=message,
        )

    async def close(self) -> None:
        """Close the producer and underlying connection."""
        if self._producer is not None:
            await self._producer.close()
            self._producer = None

    async def __aenter__(self) -> StreamPublisher:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
