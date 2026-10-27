# AI Knowledge Inbox (Local RAG)

A small production-style web app: **save notes or URLs → ask questions → get answers with cited sources**.

Everything runs **locally** with Ollama. No paid API keys.

| Layer | Choice |
|-------|--------|
| Backend | Python + FastAPI |
| Frontend | React (Vite) |
| LLM | Ollama `qwen3:4b` |
| Embeddings | Ollama `nomic-embed-text` |
| Item store | SQLite (`backend/data/items.db`) |
| Vector store | Chroma (`backend/data/chroma`) |
| URL fetch | httpx + BeautifulSoup |

---

## Prerequisites

1. **Python 3.10+**
2. **Node.js 18+**
3. **[Ollama](https://ollama.com)** installed and running

Pull models:

```bash
ollama pull qwen3:4b
ollama pull nomic-embed-text
ollama list
```

---

## How to run

### Terminal 1 — backend

```powershell
cd backend
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

If port 8000 is busy:

```powershell
uvicorn main:app --reload --port 8001
```

Then set frontend API base (optional): create `frontend/.env` with  
`VITE_API_BASE=http://localhost:8001`

### Terminal 2 — frontend

```powershell
cd frontend
npm install
npm run dev
```

Open UI: http://localhost:5173

---

## What you can do in the UI

1. **Add a note** — plain text saved to SQLite, chunked, embedded, stored in Chroma  
2. **Add a URL** — validated, page text fetched server-side, then same indexing path  
3. **List saved items** — from SQLite  
4. **Ask a question** — semantic retrieval + LLM answer + source snippets  

---

## API

| Method | Path | Body | Purpose |
|--------|------|------|---------|
| GET | `/health` | — | Liveness + model names |
| POST | `/ingest` | `{ "type": "note"\|"url", "content": "..." }` | Save + index |
| GET | `/items` | — | List saved items |
| POST | `/query` | `{ "question": "..." }` | RAG answer + sources |

### URL validation (bad URLs are rejected with HTTP 400)

- Empty / malformed URLs  
- Non-`http`/`https` schemes  
- Localhost targets  
- Timeouts / unreachable hosts  
- HTTP 4xx/5xx  
- Pages with almost no readable text  

---

## Project structure (modular — no god files)

```text
backend/
  main.py              # HTTP routes only
  models.py            # Pydantic request/response schemas
  config.py            # env + model/chunk settings
  storage.py           # SQLite persistence
  ingest.py            # orchestrate resolve + index
  url_utils.py         # URL validate + fetch/parse
  rag/
    chunking.py        # split text
    embeddings.py      # Ollama embeddings
    vector_store.py    # Chroma add/search
    pipeline.py        # retrieve + generate answer
  scripts/             # local debug helpers
frontend/
  src/api.js           # HTTP client
  src/App.jsx          # page state
  src/components/      # IngestForm, ItemList, QueryPanel
```

---

## Design tradeoffs (interview talking points)

| Topic | Choice | Why / what breaks at scale |
|-------|--------|----------------------------|
| Chunking | ~500 chars, 50 overlap | Simple + intentional; huge docs → many embeddings, slower ingest |
| Vector store | Local Chroma | Easy single-user demo; not multi-tenant / HA |
| Embeddings + LLM | Local Ollama | Free/private; slower on CPU, quality depends on hardware |
| URL fetch | Sync httpx in request | Fine for demo; production needs async workers + better extraction |
| Auth | None | Assignment scope; production needs auth + per-user isolation |

**Production upgrades:** auth, queues for ingest, hybrid search, stronger HTML cleaning, eval of retrieval, managed vector DB (Qdrant/Pinecone/pgvector).

---

## Quick smoke tests

```powershell
cd backend
.\.venv\Scripts\activate
python scripts\inspect_sqlite.py
python scripts\test_phase3.py
python scripts\test_phase4.py "What uses the V8 engine?"
python -c "from url_utils import validate_url; print(validate_url('https://example.com'))"
```

See **IMPLEMENTATION.md** for the full step-by-step pipeline (tools used at each stage).
