"""FastAPI entrypoint — thin HTTP layer for the AI Knowledge Inbox."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import OLLAMA_EMBED_MODEL, OLLAMA_LLM_MODEL
from ingest import IngestError, index_item, resolve_content
from models import (
    IngestRequest,
    IngestResponse,
    ItemResponse,
    QueryRequest,
    QueryResponse,
)
from rag.pipeline import LlmTimeoutError, run_query
from storage import create_item, init_db, list_items, preview_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("knowledge_inbox")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info(
        "DB ready | LLM=%s | embed=%s",
        OLLAMA_LLM_MODEL,
        OLLAMA_EMBED_MODEL,
    )
    yield


app = FastAPI(
    title="AI Knowledge Inbox",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_item_response(row: dict) -> ItemResponse:
    created = row["created_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created)

    return ItemResponse(
        id=row["id"],
        source_type=row["source_type"],
        source=row["source"],
        preview=preview_text(row["raw_content"]),
        created_at=created,
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_model": OLLAMA_LLM_MODEL,
        "embed_model": OLLAMA_EMBED_MODEL,
    }


@app.post("/ingest", response_model=IngestResponse)
def ingest(body: IngestRequest):
    """Save a note or URL, then chunk/embed into Chroma."""
    logger.info("ingest request type=%s content_len=%s", body.type, len(body.content))

    try:
        source_label, raw_content = resolve_content(body.type, body.content)
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ingest resolve failed")
        raise HTTPException(status_code=500, detail="failed to resolve content") from exc

    if not raw_content.strip():
        raise HTTPException(status_code=400, detail="content resolved to empty text")

    item = create_item(body.type, source_label, raw_content)

    try:
        index_item(item["id"], body.type, source_label, raw_content)
    except Exception as exc:
        logger.exception("indexing failed for item %s", item["id"])
        raise HTTPException(
            status_code=500,
            detail="item saved but indexing failed",
        ) from exc

    logger.info("ingested item_id=%s type=%s", item["id"], body.type)
    return IngestResponse(item=_to_item_response(item))


@app.get("/items", response_model=list[ItemResponse])
def get_items():
    rows = list_items()
    logger.info("listed items count=%s", len(rows))
    return [_to_item_response(row) for row in rows]


@app.post("/query", response_model=QueryResponse)
def query(body: QueryRequest):
    """Ask a question over saved content (RAG)."""
    logger.info("query request question_len=%s", len(body.question))
    try:
        answer, sources = run_query(body.question)
        logger.info("query ok sources=%s answer_len=%s", len(sources), len(answer))
        return QueryResponse(answer=answer, sources=sources)
    except LlmTimeoutError as exc:
        logger.error("query timed out: %s", exc)
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("query failed")
        raise HTTPException(
            status_code=500,
            detail="query failed — check that Ollama is running",
        ) from exc
