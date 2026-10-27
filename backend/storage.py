"""SQLite persistence for ingested notes and URLs."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from config import SQLITE_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def create_item(source_type: str, source: str, raw_content: str) -> dict[str, Any]:
    """Insert a new item and return it as a dict."""
    created_at = _utc_now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO items (source_type, source, raw_content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source_type, source, raw_content, created_at),
        )
        item_id = cursor.lastrowid

    return {
        "id": item_id,
        "source_type": source_type,
        "source": source,
        "raw_content": raw_content,
        "created_at": created_at,
    }


def list_items() -> list[dict[str, Any]]:
    """Return all items, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, source_type, source, raw_content, created_at
            FROM items
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_item(item_id: int) -> dict[str, Any] | None:
    """Fetch a single item by id, or None."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, source_type, source, raw_content, created_at
            FROM items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()

    return dict(row) if row else None


def preview_text(raw_content: str, max_len: int = 120) -> str:
    text = " ".join(raw_content.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
