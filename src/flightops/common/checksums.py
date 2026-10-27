"""Memory-efficient checksum helpers."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import BinaryIO


def stream_sha256(stream: BinaryIO, block_size: int = 1024 * 1024) -> tuple[str, int]:
    """Return a stream's SHA-256 and byte count without retaining its content."""

    digest = sha256()
    size = 0
    for block in iter(lambda: stream.read(block_size), b""):
        digest.update(block)
        size += len(block)
    return digest.hexdigest(), size


def file_sha256(path: Path, block_size: int = 1024 * 1024) -> str:
    """Return a file's SHA-256 without loading it into memory."""

    with path.open("rb") as source:
        return stream_sha256(source, block_size)[0]
