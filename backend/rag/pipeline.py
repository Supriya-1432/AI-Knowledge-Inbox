"""RAG pipeline: retrieve relevant chunks, then generate an answer with Ollama."""

from __future__ import annotations

import logging
import re

import httpx

from config import (
    LLM_MAX_SNIPPET_CHARS,
    LLM_NUM_PREDICT,
    LLM_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_LLM_MODEL,
    TOP_K,
)
from models import SourceSnippet
from rag.embeddings import embed_query
from rag.vector_store import search_similar

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You answer questions using ONLY the provided context.

Rules:
- Reply with the FINAL answer only.
- Prefer 3-6 short bullet points, or one short paragraph.
- Do NOT narrate your reasoning.
- Do NOT say phrases like "Let me analyze", "Let me check", "Looking at the snippets".
- Do NOT quote the context at length.
- If context is insufficient, say you don't know.
- You may cite sources like [1] or [2].
"""

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_TAIL_RE = re.compile(r"^.*?</think>\s*", re.DOTALL | re.IGNORECASE)
_REASONING_START_RE = re.compile(
    r"^(let me analyze|let me check|let's analyze|i'll analyze|looking at|"
    r"i need to|okay,|hmm,|the question asks)",
    re.IGNORECASE,
)
_FINAL_MARKERS_RE = re.compile(
    r"(?:final answer|direct answer|concise answer|answer:)\s*",
    re.IGNORECASE,
)


class LlmTimeoutError(TimeoutError):
    """Raised when the local LLM takes too long to answer."""


def _clip(text: str, max_chars: int = LLM_MAX_SNIPPET_CHARS) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def build_prompt(question: str, sources: list[dict]) -> str:
    """Build the user prompt with numbered context blocks (clipped for speed)."""
    if not sources:
        context = "(no relevant context found)"
    else:
        parts = []
        for i, src in enumerate(sources, start=1):
            parts.append(
                f"[{i}] (item_id={src['item_id']}, {src['source_type']})\n"
                f"{_clip(src['snippet'])}"
            )
        context = "\n\n".join(parts)

    # /no_think first — qwen3 often ignores later placement
    return (
        "/no_think\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Write only the final answer now:"
    )


def _strip_think_tags(text: str) -> str:
    cleaned = _THINK_BLOCK_RE.sub("", text or "")
    if "</think>" in cleaned.lower():
        cleaned = _THINK_TAIL_RE.sub("", cleaned)
    return cleaned.strip()


def _looks_like_reasoning(text: str) -> bool:
    head = text[:240].lower()
    markers = (
        "let me analyze",
        "let me check",
        "looking at the",
        "the question asks",
        "this snippet",
        "from this snippet",
        "i can see that",
        "doesn't directly talk",
    )
    return any(m in head for m in markers) or bool(_REASONING_START_RE.match(text.strip()))


def _extract_useful_points(text: str) -> str:
    """If the model dumped analysis, keep the most answer-like lines."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    keep: list[str] = []
    skip_prefixes = (
        "let me ",
        "let's ",
        "i'll ",
        "i will ",
        "the question asks",
        "looking at",
        "this snippet",
        "so from this",
        "from this snippet",
        "snippet [",
        "[",
        "okay",
        "hmm",
    )
    for line in lines:
        low = line.lower()
        if any(low.startswith(p) for p in skip_prefixes):
            continue
        if low.startswith("so,") and "snippet" in low:
            continue
        # Keep bullets / concrete feature-like lines
        if line.startswith(("-", "*", "•")) or any(
            key in low
            for key in (
                "easy to use",
                "budget",
                "hosting",
                "feature",
                "payment",
                "builder",
                "look for",
                "should",
                "include",
            )
        ):
            keep.append(line)

    if keep:
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for item in keep:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return "\n".join(unique[:8])

    # Fallback: last non-meta paragraph
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for para in reversed(paragraphs):
        if not _looks_like_reasoning(para) and len(para) > 40:
            return para
    return text.strip()


def _clean_answer(text: str) -> str:
    cleaned = _strip_think_tags(text)
    if not cleaned:
        return ""

    # Prefer explicit "Final answer:" style endings when present
    marker_split = _FINAL_MARKERS_RE.split(cleaned)
    if len(marker_split) > 1 and marker_split[-1].strip():
        candidate = marker_split[-1].strip()
        if len(candidate) > 20:
            cleaned = candidate

    if _looks_like_reasoning(cleaned):
        cleaned = _extract_useful_points(cleaned)

    return cleaned.strip()


def generate_answer(question: str, sources: list[dict]) -> str:
    """Call local Ollama chat API with retrieved context."""
    prompt = build_prompt(question, sources)
    payload = {
        "model": OLLAMA_LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,
            "num_predict": LLM_NUM_PREDICT,
        },
    }

    logger.info(
        "calling Ollama LLM=%s chunks=%s prompt_chars=%s timeout=%ss",
        OLLAMA_LLM_MODEL,
        len(sources),
        len(prompt),
        LLM_TIMEOUT_SECONDS,
    )

    try:
        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        logger.error("Ollama LLM timed out after %ss", LLM_TIMEOUT_SECONDS)
        raise LlmTimeoutError(
            f"Local model '{OLLAMA_LLM_MODEL}' timed out after {int(LLM_TIMEOUT_SECONDS)}s. "
            "Try again, use a shorter question, or keep Ollama running with the model loaded."
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Ollama LLM request failed")
        raise RuntimeError(
            f"Could not reach Ollama at {OLLAMA_BASE_URL}. Is it running?"
        ) from exc

    message = data.get("message") or {}
    # Newer Ollama/qwen3 may put private reasoning in "thinking" — ignore it
    if message.get("thinking"):
        logger.info("ignoring Ollama thinking field (%s chars)", len(message["thinking"]))
    content = message.get("content") or data.get("response") or ""
    answer = _clean_answer(content)
    if not answer:
        answer = "I couldn't produce a clean answer from the model output. Please try again."
    return answer


def run_query(question: str, top_k: int = TOP_K) -> tuple[str, list[SourceSnippet]]:
    """Full RAG path: embed question → retrieve → generate → package sources."""
    query_vec = embed_query(question)
    hits = search_similar(query_vec, top_k=top_k)

    if not hits:
        answer = (
            "I don't have any indexed content to search yet. "
            "Save a note or URL first, then ask again."
        )
        return answer, []

    logger.info(
        "query retrieve hits=%s top_item_ids=%s",
        len(hits),
        [h["item_id"] for h in hits],
    )
    answer = generate_answer(question, hits)
    logger.info("query generate answer_len=%s", len(answer))
    sources = [
        SourceSnippet(
            item_id=hit["item_id"],
            source_type=hit["source_type"],
            source=hit["source"],
            snippet=hit["snippet"],
        )
        for hit in hits
    ]
    return answer, sources
