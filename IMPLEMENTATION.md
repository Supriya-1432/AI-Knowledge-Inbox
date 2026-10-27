# Implementation guide — end to end

---

## Tools used at each step (ingest → answer)

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 1. USER INPUT (React UI)                                             │
│    tool: frontend/src/components/IngestForm.jsx + api.js             │
│    sends POST /ingest  { type: "note"|"url", content: "..." }        │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 2. HTTP LAYER                                                        │
│    tool: FastAPI (backend/main.py)                                   │
│    validates body with Pydantic (backend/models.py)                  │
│    logs request; returns clear 400/500 errors                        │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 3. RESOLVE CONTENT                                                   │
│    tool: backend/ingest.py → resolve_content()                       │
│                                                                      │
│    NOTE path:                                                        │
│      use plain text as-is                                            │
│                                                                      │
│    URL path:                                                         │
│      backend/url_utils.py                                            │
│        validate_url()  → scheme/host checks, reject bad URLs         │
│        fetch_url_text()→ httpx GET + BeautifulSoup text extract      │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 4. PERSIST ORIGINAL ITEM                                             │
│    tool: SQLite via backend/storage.py                               │
│    file: backend/data/items.db                                       │
│    stores: id, source_type, source, raw_content, created_at          │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 5. CHUNK TEXT                                                        │
│    tool: backend/rag/chunking.py                                     │
│    config: CHUNK_SIZE=500, CHUNK_OVERLAP=50 (backend/config.py)      │
│    output: list of overlapping text pieces                           │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 6. EMBED CHUNKS (WRITE PATH)                                         │
│    tool: Ollama nomic-embed-text via backend/rag/embeddings.py       │
│    API: POST http://localhost:11434/api/embeddings                   │
│    output: one 768-dim vector per chunk                              │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 7. STORE VECTORS                                                     │
│    tool: Chroma PersistentClient (backend/rag/vector_store.py)       │
│    path: backend/data/chroma                                         │
│    collection: "knowledge_inbox"                                     │
│    each record: id, document (chunk text), embedding, metadata       │
└──────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────┐
│ 8. USER ASKS A QUESTION (React QueryPanel)                           │
│    tool: frontend → POST /query { question }                         │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 9. EMBED QUESTION (READ PATH — NOT SAVED TO CHROMA)                  │
│    tool: same Ollama nomic-embed-text (embed_query)                  │
│    question vector lives only in memory for comparison               │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 10. SEMANTIC RETRIEVAL                                               │
│     tool: Chroma query (cosine similarity)                           │
│     returns top-k chunk texts + metadata (item_id, source, …)        │
│     this is vector similarity / semantic search (not keyword search) │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 11. GENERATE ANSWER                                                  │
│     tool: Ollama qwen3:4b via backend/rag/pipeline.py                │
│     API: POST http://localhost:11434/api/chat                        │
│     prompt = system rules + retrieved context + question             │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 12. DISPLAY IN UI                                                    │
│     answer text + source snippets (item id, type, URL/note, chunk)   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Module responsibilities

| File | Responsibility |
|------|----------------|
| `main.py` | Routes, HTTP status codes, CORS, top-level logging |
| `models.py` | Request/response schemas + input validation |
| `storage.py` | SQLite CRUD for inbox items |
| `url_utils.py` | URL validation + HTML fetch/clean |
| `ingest.py` | Glue: resolve content → save → index |
| `rag/chunking.py` | Split text |
| `rag/embeddings.py` | Talk to Ollama embeddings |
| `rag/vector_store.py` | Chroma add + search |
| `rag/pipeline.py` | Full query RAG orchestration |
| `frontend/src/api.js` | Browser → backend calls |
| `frontend/src/components/*` | UI sections (ingest / list / ask) |

---

## Logging

Structured-ish logs (timestamp, level, module) cover:

- ingest request / resolve / index start+complete  
- URL validate / fetch success or rejection  
- chunking sizes  
- embedding progress  
- Chroma add/search counts  
- query retrieve + generate  

Watch them in the uvicorn terminal while you use the app.

---