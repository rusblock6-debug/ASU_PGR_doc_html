import time
from dataclasses import dataclass, field
from itertools import chain

from app.models.types import NanoID
from app.protocol.codec import Chunk
from app.protocol.compression import decompress


@dataclass
class MessageIn:
    """Buffer of message chunks for reassembly"""

    msg_id: NanoID
    total_chunks: int
    chunks: dict[int, Chunk] = field(default_factory=dict)
    is_compressed: bool | None = None
    created_at: float = field(default_factory=time.monotonic)
    data: bytes | None = None
    are_callbacks_called: bool = False

    def add_chunk(self, chunk: Chunk) -> None:
        """Add chunk"""
        if chunk.msg_id != self.msg_id:
            raise ValueError(
                f"Chunk msg_id {chunk.msg_id} does not match buffer {self.msg_id}"
            )
        if chunk.total != self.total_chunks:
            raise ValueError(
                f"Chunk total {chunk.total} does not match buffer total {self.total_chunks}"
            )

        # Note: set compression flag only when first chunk is added
        if self.is_compressed is None:
            self.is_compressed = chunk.is_compressed

        self.chunks[chunk.index] = chunk

    @property
    def are_all_chunks_in_place(self) -> bool:
        """Check if all chunks have been received"""
        return len(self.chunks) == self.total_chunks and all(
            index in self.chunks for index in range(self.total_chunks)
        )

    def get_chunk_indices(self) -> set[int]:
        """Get indices of present chunks"""
        if self.are_callbacks_called:
            return set(range(self.total_chunks))
        return set(self.chunks)

    def assemble(self) -> bytes:
        """Assemble the complete message from chunks"""

        if self.data is not None:
            return self.data

        data = b""
        for index in range(self.total_chunks):
            data += self.chunks[index].payload

        if self.is_compressed:
            data = decompress(data)

        self.data = data
        return self.data

    def spare_memory(self) -> None:
        self.data = None
        self.chunks.clear()


class Reassembler:
    """Manages reassembly of multiple messages"""

    def __init__(self) -> None:
        self._messages: dict[NanoID, MessageIn] = {}

    def get(self, msg_id: NanoID) -> MessageIn | None:
        """Get message (if present)"""
        if msg_id not in self._messages:
            return None
        return self._messages[msg_id]

    def add(self, message: MessageIn) -> None:
        """Add message"""
        self._messages[message.msg_id] = message

    def delete(self, msg_id: NanoID) -> None:
        """Delete stored message"""
        if msg_id in self._messages:
            del self._messages[msg_id]

    def clean(self, max_age_seconds: int) -> tuple[list[NanoID], list[NanoID]]:
        """Clean messages older than max_age_seconds."""
        now = time.monotonic()
        assembled, incomplete = [], []

        for msg_id, message in self._messages.items():
            if now - message.created_at > max_age_seconds:
                if message.are_callbacks_called:
                    assembled.append(msg_id)
                elif message.data is None:
                    incomplete.append(msg_id)

        list(map(self.delete, chain(assembled, incomplete)))

        return assembled, incomplete
