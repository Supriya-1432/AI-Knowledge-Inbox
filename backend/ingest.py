"""Content ingestion orchestration: notes, URLs, then RAG indexing."""

from __future__ import annotations

import logging

from rag.chunking import chunk_text
from rag.embeddings import embed_texts
from rag.vector_store import add_chunks
from url_utils import UrlFetchError, UrlValidationError, fetch_url_text, validate_url

logger = logging.getLogger(__name__)


class IngestError(Exception):
    """Raised when content cannot be ingested."""


def resolve_content(source_type: str, content: str) -> tuple[str, str]:
    """Return (source_label, raw_content) ready for SQLite + indexing.

    - note → ("note", plain text)
    - url  → (canonical url, fetched page text)
    """
    if source_type == "note":
        text = content.strip()
        if not text:
            raise IngestError("note content is empty")
        logger.info("resolved note chars=%s", len(text))
        return "note", text

    if source_type == "url":
        try:
            cleaned_url = validate_url(content)
            raw = fetch_url_text(cleaned_url)
        except (UrlValidationError, UrlFetchError) as exc:
            logger.warning("url ingest rejected: %s", exc)
            raise IngestError(str(exc)) from exc
        return cleaned_url, raw

    raise IngestError(f"unsupported source_type: {source_type}")


def index_item(item_id: int, source_type: str, source: str, raw_content: str) -> None:
    """Chunk → embed → store vectors for one item."""
    logger.info(
        "index start item_id=%s type=%s source=%s chars=%s",
        item_id,
        source_type,
        source,
        len(raw_content),
    )

    chunks = chunk_text(raw_content)
    if not chunks:
        logger.warning("no chunks produced for item_id=%s", item_id)
        return

    logger.info("index chunked item_id=%s chunks=%s", item_id, len(chunks))
    embeddings = embed_texts(chunks)
    add_chunks(
        item_id,
        chunks,
        embeddings,
        {
            "source_type": source_type,
            "source": source,
        },
    )
    logger.info("index complete item_id=%s chunks=%s", item_id, len(chunks))
