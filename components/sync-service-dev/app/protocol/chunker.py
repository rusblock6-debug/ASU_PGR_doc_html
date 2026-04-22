from typing import List

from app.models.types import NanoID
from app.protocol.codec import Chunk
from app.settings import settings


def calc_total_chunks(data: bytes) -> int:
    """
    Calculate total number of chunks needed for a message.

    **IMPORTANT**
    Do not forget to pass data AFTER compression (if used)
    """
    return (len(data) + settings.payload_size - 1) // settings.payload_size


def chunk_message(
    data: bytes,
    msg_id: NanoID,
    deduplication: bool = False,
    is_compressed: bool = False,
) -> List[Chunk]:
    """
    Fragment a message into chunks.

    Args:
        data: Message payload to fragment
        msg_id: Message ID
        delivery_mode: Delivery guarantee mode
        is_compressed: Compressed sign

    Returns:
        List of Chunk objects

    Raises:
        ValueError: If message exceeds max size or chunk limit
    """
    # Check original size limit before compression
    if len(data) > settings.max_size:
        raise ValueError(
            f"Message size {len(data)} exceeds maximum {settings.max_size}"
        )

    chunks = []

    # Calculate number of chunks needed for msg_data (compressed or original)
    total_chunks = calc_total_chunks(data)

    # Validate chunk count against uint16 limit (max 65535 chunks)
    if total_chunks > 65535:
        max_size = 65535 * settings.payload_size
        raise ValueError(
            f"Message requires {total_chunks} chunks, exceeding uint16 limit. "
            f"Maximum effective message size is {max_size} bytes with current chunk size."
        )

    for index in range(total_chunks):
        start = index * settings.payload_size
        end = min(start + settings.payload_size, len(data))
        payload = data[start:end]

        flags = 0
        if deduplication:
            flags |= 0b00000010  # Set deduplication bit
        if is_compressed:
            flags |= 0b00000100  # Set compression bit

        chunk = Chunk(
            msg_id=msg_id,
            index=index,
            total=total_chunks,
            flags=flags,
            payload=payload,
        )
        chunks.append(chunk)

    return chunks
