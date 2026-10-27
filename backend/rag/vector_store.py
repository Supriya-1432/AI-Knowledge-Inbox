"""Local Chroma vector store for chunk embeddings."""

from __future__ import annotations

import logging
from typing import Any

from config import CHROMA_PATH, TOP_K

logger = logging.getLogger(__name__)

_collection = None


def get_collection():
    """Return (and cache) the Chroma collection on disk under data/chroma."""
    global _collection
    if _collection is not None:
        return _collection

    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    _collection = client.get_or_create_collection(
        name="knowledge_inbox",
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def add_chunks(
    item_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: dict[str, Any],
) -> None:
    """Store chunk texts + embeddings for one ingested item."""
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length must match")
    if not chunks:
        logger.warning("add_chunks called with no chunks for item_id=%s", item_id)
        return

    collection = get_collection()
    ids = [f"{item_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            **metadata,
            "item_id": item_id,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info("stored %s chunks in Chroma for item_id=%s", len(chunks), item_id)


def search_similar(
    query_embedding: list[float],
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Compare query vector to stored vectors; return top-k chunk hits.

    Important: this does NOT write the query embedding into Chroma.
    It only uses it for similarity comparison against existing records.
    """
    collection = get_collection()
    total = collection.count()
    if total == 0:
        logger.info("Chroma collection empty — nothing to retrieve")
        return []

    n_results = min(top_k, total)
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    hits: list[dict[str, Any]] = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        meta = meta or {}
        hits.append(
            {
                "item_id": int(meta.get("item_id", 0)),
                "snippet": doc or "",
                "source_type": meta.get("source_type", "note"),
                "source": meta.get("source", "unknown"),
                "distance": distance,
            }
        )

    logger.info("retrieved %s chunks (collection size=%s)", len(hits), total)
    return hits


def count_chunks() -> int:
    """How many vectors are currently stored (handy for debugging)."""
    return get_collection().count()
