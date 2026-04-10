import time
from dataclasses import dataclass, field
from itertools import chain

from app.models.schemas import DeliveryParams
from app.models.types import NanoID
from app.protocol.chunker import chunk_message
from app.protocol.codec import Chunk
from app.protocol.compression import compress


@dataclass
class MessageOut:
    """Buffer of message chunks for delivery"""

    msg_id: NanoID
    params: DeliveryParams
    total_chunks: int
    total_size: int
    is_compressed: bool
    chunks: dict[int, Chunk] | None
    acked: set[int] = field(default_factory=set, repr=False)
    created_at: float = field(default_factory=time.monotonic)

    @property
    def is_sending(self) -> bool:
        return self.chunks is not None and self.total_chunks != len(self.acked)

    @property
    def is_sent(self) -> bool:
        return self.chunks is None and self.total_chunks == len(self.acked)

    @property
    def is_failed(self) -> bool:
        return self.chunks is None and self.total_chunks != len(self.acked)

    @property
    def chunks_list(self) -> list[Chunk]:
        """Safely get list of chunks"""
        if not self.chunks:
            return []
        return list(self.chunks.values())


class Disassembler:
    """Manages disassembly of multiple messages"""

    def __init__(self):
        self._messages: dict[NanoID, MessageOut] = {}

    def get(self, msg_id: NanoID) -> MessageOut | None:
        """Get message (if present)"""
        if msg_id not in self._messages:
            return None
        return self._messages[msg_id]

    def add(self, msg_id: NanoID, data: bytes, params: DeliveryParams) -> MessageOut:
        """Comporess, chunk and store message in memory"""

        c_data, is_compressed = compress(data)
        chunks = chunk_message(c_data, msg_id, params.deduplication, is_compressed)

        message = MessageOut(
            msg_id=msg_id,
            params=params,
            total_chunks=len(chunks),
            total_size=len(c_data),
            is_compressed=is_compressed,
            chunks={
                chunk.index: chunk
                for chunk in chunks
            }
        )
        self._messages[message.msg_id] = message
        return message

    def delete(self, msg_id: NanoID) -> None:
        """Delete stored message"""
        if msg_id not in self._messages:
            return
        del self._messages[msg_id]

    def delete_chunks(self, msg_id: NanoID) -> None:
        """Delete stored chunks"""
        if msg_id not in self._messages:
            return
        self._messages[msg_id].chunks = None

    def clean(self, max_age_seconds: int) -> tuple[list[NanoID], list[NanoID]]:
        """Clean messages older than max_age_seconds"""
        now = time.monotonic()
        sent, failed = [], []

        for msg_id, message in self._messages.items():
            if now - message.created_at > max_age_seconds:
                if message.is_sent:
                    sent.append(msg_id)
                elif message.is_failed:
                    failed.append(msg_id)

        list(map(self.delete, chain(sent, failed)))

        return sent, failed

    def get_chunk(self, msg_id: NanoID, index: int) -> Chunk | None:
        """Find chunk by msg_id and index (if present)"""
        msg = self.get(msg_id)
        if msg is None or msg.chunks is None:
            return
        return msg.chunks.get(index)

    def get_acked_indices(self, msg_id: NanoID) -> set[int]:
        """Get indices of acked chunks by msg_id"""
        msg = self.get(msg_id)
        if msg is None:
            return set()
        return msg.acked

    def get_unacked_indices(self, msg_id: NanoID) -> set[int]:
        """Get indices of UNacked chunks by msg_id"""
        msg = self.get(msg_id)
        if msg is None:
            return set()
        return set(range(msg.total_chunks)) - msg.acked
