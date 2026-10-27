"""App configuration — local Ollama only, no paid APIs."""

from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# SQLite for saved notes / URLs
SQLITE_PATH = DATA_DIR / "items.db"

# Chroma persistence folder for embeddings
CHROMA_PATH = DATA_DIR / "chroma"

# Ollama (must be running locally: http://localhost:11434)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen3:4b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Chunking defaults (tweak later; document rationale in README)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# How many chunks to retrieve per question
TOP_K = int(os.getenv("TOP_K", "3"))

# Local LLM can be slow on CPU — keep timeouts generous, prompts short
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "600"))
LLM_MAX_SNIPPET_CHARS = int(os.getenv("LLM_MAX_SNIPPET_CHARS", "350"))
LLM_NUM_PREDICT = int(os.getenv("LLM_NUM_PREDICT", "320"))

