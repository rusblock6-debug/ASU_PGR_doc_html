import struct
from dataclasses import dataclass

from app.models.types import NanoID
from app.settings import settings


@dataclass
class Chunk:
    """Represents a single message chunk."""

    msg_id: NanoID
    index: int
    total: int
    flags: int
    payload: bytes

    @property
    def is_ack(self) -> bool:
        """Check if this is an ACK chunk."""
        return bool(self.flags & 0b00000001)

    @property
    def deduplication(self) -> bool:
        """Check if message needs to be deduplicated."""
        return bool(self.flags & 0b00000010)

    @property
    def is_compressed(self) -> bool:
        """Check if this chunk contains compressed data."""
        return bool(self.flags & 0b00000100)

    def to_bytes(self) -> bytes:
        """Encode chunk to bytes with variable-length nanoid."""

        # Encode nanoid as UTF-8 bytes
        msg_id_bytes = self.msg_id.encode()
        # Validate length matches settings
        if len(msg_id_bytes) != settings.id_length:
            raise ValueError(
                f"Actual message ID length {len(msg_id_bytes)} doesn't match settings.id_length {settings.id_length}"
            )

        return struct.pack(
            f"!{settings.id_length}sHHB{len(self.payload)}s",
            msg_id_bytes,
            self.index,
            self.total,
            self.flags,
            self.payload
        )

    @staticmethod
    def from_bytes(data: bytes) -> "Chunk":
        """Decode chunk from bytes with variable-length nanoid."""

        # Calculate expected header size: nanoid + index + total + flags
        expected_header_size = settings.id_length + 2 + 2 + 1  # nanoid + index + total + flags
        if len(data) < expected_header_size:
            raise ValueError(f"Chunk too small: {len(data)} bytes, expected header {expected_header_size}")
        expected_payload_size = len(data) - expected_header_size

        # Unpack full header
        msg_id_bytes, index, total, flags, payload = struct.unpack_from(
            f"!{settings.id_length}sHHB{expected_payload_size}s", data
        )

        # Validate chunk fields
        if total == 0:
            raise ValueError("Invalid chunk: total chunks must be > 0")
        if total > 65535:  # uint16 max
            raise ValueError(f"Invalid chunk: total chunks {total} exceeds uint16 limit (65535)")
        if index >= total:
            raise ValueError(f"Invalid chunk: index {index} must be < total {total}")
        if len(payload) > settings.payload_size:
            raise ValueError(f"Invalid chunk: payload size {len(payload)} exceeds maximum {settings.payload_size}")

        # Decode nanoid from UTF-8 bytes
        try:
            msg_id_str = msg_id_bytes.decode()
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid UTF-8 in nanoid bytes: {e}")

        return Chunk(
            msg_id=NanoID(msg_id_str),
            index=index,
            total=total,
            flags=flags,
            payload=payload,
        )

    @staticmethod
    def create_ack(msg_id: NanoID, received_indices: set[int], total_chunks: int) -> "Chunk":
        """
        Create an ACK chunk with flexible format.

        For messages with ≤64 chunks: uses 64-bit bitmap (8 bytes)
        For messages with >64 chunks: uses range-based format (more compact)

        Range format: num_ranges (2 bytes) + [start, count] pairs (4 bytes each)
        Example: chunks {0,1,2,10,11,12,13} -> 2 ranges: [0,3], [10,4]
        """
        if total_chunks <= 64:
            # Use bitmap format for small messages
            bitmap = 0
            for index in received_indices:
                if index < 64:
                    bitmap |= (1 << index)
            payload = struct.pack("!Q", bitmap)
        else:
            # Use range-based format for large messages
            # Convert chunks to consecutive ranges for efficient encoding
            sorted_indices = sorted(received_indices)

            if not sorted_indices:
                payload = struct.pack("!H", 0)  # No ranges
            else:
                ranges = []
                range_start = sorted_indices[0]
                range_count = 1

                for i in range(1, len(sorted_indices)):
                    if sorted_indices[i] == sorted_indices[i-1] + 1:
                        # Continue current range
                        range_count += 1
                    else:
                        # Save current range and start new one
                        ranges.append((range_start, range_count))
                        range_start = sorted_indices[i]
                        range_count = 1

                # Save last range
                ranges.append((range_start, range_count))

                # Pack ranges: num_ranges + (start, count) pairs
                payload = struct.pack(
                    f"!H{len(ranges) * 2}H",
                    len(ranges),
                    *[val for r in ranges for val in r]
                )

        return Chunk(
            msg_id=msg_id,
            index=0,
            total=total_chunks,
            flags=0b00000001,  # is_ack
            payload=payload,
        )

    def get_acked_indices(self) -> set[int]:
        """
        Extract acknowledged chunk indices from ACK payload.

        Handles both bitmap format (≤64 chunks) and range format (>64 chunks).
        """
        if not self.is_ack:
            raise ValueError("Not an ACK chunk")

        if self.total <= 64:
            # Bitmap format
            bitmap = struct.unpack("!Q", self.payload[:8])[0]
            acked = set()
            for i in range(min(64, self.total)):
                if bitmap & (1 << i):
                    acked.add(i)
            return acked
        else:
            # Range-based format
            num_ranges = struct.unpack("!H", self.payload[:2])[0]

            if num_ranges == 0:
                return set()

            # Unpack all range data
            range_data = struct.unpack(f"!{num_ranges * 2}H", self.payload[2:2 + num_ranges * 4])

            # Convert ranges back to individual chunk IDs
            acked = set()
            for i in range(0, len(range_data), 2):
                start = range_data[i]
                count = range_data[i + 1]
                for chunk_id in range(start, start + count):
                    acked.add(chunk_id)

            return acked
