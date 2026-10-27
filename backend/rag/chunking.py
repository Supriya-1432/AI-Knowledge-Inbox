"""Split raw text into overlapping chunks for embedding."""

from __future__ import annotations

import logging

from config import CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Return overlapping character chunks.

    Why these defaults:
    - chunk_size ~500: small enough for precise retrieval, large enough for context
    - overlap ~50: preserves meaning when a sentence straddles a boundary
    """
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        logger.info("chunking skipped: empty text")
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    if len(cleaned) <= chunk_size:
        logger.info("chunking chars=%s chunks=1 (single chunk)", len(cleaned))
        return [cleaned]

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(cleaned):
        end = start + chunk_size
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start += step

    logger.info(
        "chunking chars=%s chunk_size=%s overlap=%s chunks=%s",
        len(cleaned),
        chunk_size,
        overlap,
        len(chunks),
    )
    return chunks
