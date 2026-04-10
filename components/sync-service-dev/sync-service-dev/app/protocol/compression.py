import gzip
import logging
from abc import ABC, abstractmethod

import lz4.block

from app.models.types import CompressionAlgorithm
from app.settings import settings

logger = logging.getLogger("proto.compression")


class Compressor(ABC):
    """Abstract base class for compression algorithms."""

    @abstractmethod
    def compress(self, raw_data: bytes) -> bytes:
        """Compress data."""
        pass

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        pass

    @property
    @abstractmethod
    def algorithm(self) -> CompressionAlgorithm:
        """Return the compression algorithm identifier."""
        pass


class NoCompression(Compressor):
    """No compression - passthrough implementation."""

    def compress(self, raw_data: bytes) -> bytes:
        """Return data unchanged."""
        return raw_data

    def decompress(self, data: bytes) -> bytes:
        """Return data unchanged."""
        return data

    @property
    def algorithm(self) -> CompressionAlgorithm:
        """Return algorithm identifier."""
        return CompressionAlgorithm.NONE


class GzipCompressor(Compressor):
    """Gzip compression."""

    def __init__(self, compresslevel: int = 6) -> None:
        """
        Initialize gzip compressor.

        Args:
            compresslevel: Compression level (1-9). Default 6
        """
        self.compresslevel = compresslevel

    def compress(self, raw_data: bytes) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(raw_data, compresslevel=self.compresslevel)

    def decompress(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        return gzip.decompress(data)

    @property
    def algorithm(self) -> CompressionAlgorithm:
        """Return algorithm identifier."""
        return CompressionAlgorithm.GZIP


class LZ4BlockCompressor(Compressor):
    """
    LZ4 Block compression.

    The Block format is the core, low-level LZ4 compression algorithm result, without any extra information
    (headers, footers, checksums). Only the size of uncompressed data is stored if store_size set to True
    """

    def __init__(self, mode: str = "high_compression", compression: int = 9, store_size: bool = True) -> None:
        """
        Initialize lz4.block compressor.

        Args:
            mode: default, fast, or high_compression (default)
            compression: Compression level 1-12 (4-9 are recommended, default 9).
                         Only for high_compression mode.
            store_size: if True (default) then the size of the uncompressed data
                        is stored at the start of the compressed block
        """
        self.mode = mode
        self.compression = compression
        self.store_size = store_size

    def compress(self, raw_data: bytes) -> bytes:
        """Compress data using lz4.block."""
        return lz4.block.compress(
            raw_data,
            mode=self.mode,
            compression=self.compression,
            store_size=self.store_size,
        )

    def decompress(self, data: bytes) -> bytes:
        """Decompress lz4.block data."""
        return lz4.block.decompress(data)

    @property
    def algorithm(self) -> CompressionAlgorithm:
        """Return algorithm identifier."""
        return CompressionAlgorithm.LZ4B


def get_compressor(algorithm: CompressionAlgorithm, **kwargs) -> Compressor:
    """
    Factory function to get a compressor instance.

    Args:
        algorithm: Compression algorithm to use
        **kwargs: Algorithm-specific parameters

    Returns:
        Compressor instance
    """
    if algorithm == CompressionAlgorithm.NONE:
        return NoCompression()
    elif algorithm == CompressionAlgorithm.GZIP:
        gzip_kwargs = {}
        if "compresslevel" in kwargs:
            gzip_kwargs["compresslevel"] = kwargs["compresslevel"]
        return GzipCompressor(**gzip_kwargs)
    elif algorithm == CompressionAlgorithm.LZ4B:
        lz4b_kwargs = {}
        if "mode" in kwargs:
            lz4b_kwargs["mode"] = kwargs["mode"]
        if "compression" in kwargs:
            lz4b_kwargs["compression"] = kwargs["compression"]
        if "store_size" in kwargs:
            lz4b_kwargs["store_size"] = kwargs["store_size"]
        return LZ4BlockCompressor(**lz4b_kwargs)
    else:
        raise ValueError(f"Unsupported compression algorithm: {algorithm}")


def should_compress(raw_data: bytes, algorithm: CompressionAlgorithm, min_size: int = 64) -> bool:
    """
    Determine if data should be compressed based on size and algorithm.

    For very small payloads, compression overhead might not be worth it.
    Gzip has ~20-30 bytes of overhead, so we skip compression for very small data.

    Args:
        raw_data: Data to potentially compress
        algorithm: Compression algorithm
        min_size: Minimum size threshold for compression

    Returns:
        True if compression should be applied
    """
    if algorithm == CompressionAlgorithm.NONE:
        return False

    return len(raw_data) >= min_size


def compress(raw_data: bytes) -> tuple[bytes, bool]:
    """Apply compression if enabled and beneficial"""

    needs_compression = should_compress(raw_data, settings.compression_algo, settings.compression_min_size)
    data = raw_data
    if needs_compression:
        compressor = get_compressor(settings.compression_algo)
        compressed_data = compressor.compress(raw_data)
        if len(compressed_data) >= len(raw_data):
            logger.warning(
                f"Algo: {settings.compression_algo}; compressed size {len(compressed_data)} "
                f">= original size {len(raw_data)}; compression will not be engaged"
            )
            needs_compression = False
            data = raw_data
        else:
            logger.debug(
                f"Algo: {settings.compression_algo}; compressed size {len(compressed_data)} "
                f"< original size {len(raw_data)}"
            )
            data = compressed_data
    else:
        logger.debug(
            f"Algo: {settings.compression_algo}, min size: {settings.compression_min_size}, "
            f"data size: {len(raw_data)}; compression will not be engaged"
        )
    return data, needs_compression


def decompress(data: bytes) -> bytes:
    """Apply decompression"""

    compressor = get_compressor(settings.compression_algo)
    raw_data = compressor.decompress(data)
    logger.debug(
        f"Algo: {settings.compression_algo}; compressed size {len(data)}; "
        f"decompressed size {len(raw_data)}"
    )
    return raw_data
