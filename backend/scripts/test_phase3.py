"""Quick Phase 3 smoke test: chunk → embed → Chroma (no FastAPI needed).

Usage (from backend/, Ollama running):
  python scripts/test_phase3.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.chunking import chunk_text
from rag.embeddings import check_ollama_embed, embed_texts
from rag.vector_store import add_chunks, count_chunks


SAMPLE = (
    "The AI Knowledge Inbox lets users save short notes and URLs. "
    "A RAG pipeline chunks the text, embeds it with nomic-embed-text via Ollama, "
    "stores vectors in Chroma, and answers questions with qwen3:4b using retrieved context. "
    "This is a local-only setup with no paid API keys. "
    "Chunking uses about 500 characters with 50 characters of overlap between chunks."
)


def main() -> None:
    print("Ollama embed OK?", check_ollama_embed())
    chunks = chunk_text(SAMPLE)
    print(f"chunks={len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  [{i}] {len(c)} chars: {c[:70]}...")

    embeddings = embed_texts(chunks)
    print(f"vectors={len(embeddings)} dim={len(embeddings[0])}")

    add_chunks(
        item_id=9999,
        chunks=chunks,
        embeddings=embeddings,
        metadata={"source_type": "note", "source": "phase3-test"},
    )
    print(f"chroma count={count_chunks()}")
    print("Phase 3 smoke test passed.")


if __name__ == "__main__":
    main()
