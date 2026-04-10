import asyncio


class LocksStore:
    """Storage for asyncio locks."""

    receive_prefix = "lock:receive"
    retry_prefix = "lock:retry"

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}

    async def acquire_lock(self, key: str) -> None:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        await self._locks[key].acquire()

    def release_lock(self, key: str) -> None:
        if key not in self._locks:
            return
        self._locks[key].release()
        if (
            self._locks[key]._waiters is None
            or len(self._locks[key]._waiters) < 1  # type: ignore
        ):
            del self._locks[key]
