import asyncio

from app.models.types import NanoID


class ResultEvent(asyncio.Event):
    """asyncio.Event that can store a success or failure result flag."""

    def __init__(self) -> None:
        super().__init__()
        self.result: bool = False

    def set_success(self) -> None:
        super().set()
        self.result = True

    def set_failure(self) -> None:
        super().set()
        self.result = False


class EventsStore:
    """Storage for asyncio events."""

    def __init__(self):
        self._events: dict[NanoID, ResultEvent] = {}

    def create(self, msg_id: NanoID) -> None:
        if msg_id not in self._events:
            self._events[msg_id] = ResultEvent()

    def get(self, msg_id: NanoID) -> ResultEvent | None:
        return self._events.get(msg_id)

    async def wait_for_result(self, msg_id: NanoID) -> bool:
        if msg_id not in self._events:
            return False
        await self._events[msg_id].wait()
        return self._events[msg_id].result

    def set_success(self, msg_id: NanoID) -> None:
        if msg_id in self._events:
            self._events[msg_id].set_success()

    def set_failure(self, msg_id: NanoID) -> None:
        if msg_id in self._events:
            self._events[msg_id].set_failure()

    def delete(self, msg_id: NanoID) -> None:
        if msg_id in self._events:
            if len(self._events[msg_id]._waiters) < 1:
                del self._events[msg_id]
