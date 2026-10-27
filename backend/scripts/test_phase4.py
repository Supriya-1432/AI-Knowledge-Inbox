"""Phase 4 smoke test: retrieve + answer (Ollama must be running).

Usage (from backend/):
  python scripts/test_phase4.py
  python scripts/test_phase4.py "What is this project about?"
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.pipeline import run_query
from rag.vector_store import count_chunks


def main() -> None:
    question = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "What is the AI Knowledge Inbox and how does RAG work in it?"
    )
    print(f"chroma chunks={count_chunks()}")
    print(f"question={question!r}")
    answer, sources = run_query(question)
    print("\n--- answer ---")
    print(answer)
    print("\n--- sources ---")
    for s in sources:
        print(f"  item#{s.item_id} [{s.source_type}] {s.snippet[:100]}...")


if __name__ == "__main__":
    main()
