"""Generate embeddings via local Ollama (nomic-embed-text)."""

from __future__ import annotations

import logging

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL

logger = logging.getLogger(__name__)


def _embed_one(client: httpx.Client, text: str) -> list[float]:
    """Call Ollama embeddings API for a single string."""
    response = client.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
    )
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not embedding:
        raise RuntimeError(f"Ollama returned no embedding: {data}")
    return embedding


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed many strings. Returns one vector per input string."""
    if not texts:
        return []

    vectors: list[list[float]] = []
    # Longer timeout: first call may load the model into memory
    with httpx.Client(timeout=120.0) as client:
        for i, text in enumerate(texts):
            logger.info("embedding chunk %s/%s (%s chars)", i + 1, len(texts), len(text))
            vectors.append(_embed_one(client, text))

    return vectors


def embed_query(question: str) -> list[float]:
    """Embed a single question string."""
    vectors = embed_texts([question])
    return vectors[0]


def check_ollama_embed() -> bool:
    """Quick health check that the embed model responds.

    First call can be slow while Ollama loads the model into memory.
    """
    try:
        with httpx.Client(timeout=180.0) as client:
            vec = _embed_one(client, "ping")
            return bool(vec)
    except Exception:
        logger.exception("Ollama embed health check failed")
        return False
