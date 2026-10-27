"""Inspect the Knowledge Inbox SQLite DB from the terminal.

Usage (from backend/):
  python scripts/inspect_sqlite.py
  python scripts/inspect_sqlite.py --all
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import SQLITE_PATH  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect items.db")
    parser.add_argument("--all", action="store_true", help="Print full raw_content")
    args = parser.parse_args()

    print(f"DB path: {SQLITE_PATH}")
    if not SQLITE_PATH.exists():
        print("Database file does not exist yet. Start the API once to create it.")
        return

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print("Tables:", [t["name"] for t in tables])

    count = conn.execute("SELECT COUNT(*) AS n FROM items").fetchone()["n"]
    print(f"Item count: {count}\n")

    rows = conn.execute(
        """
        SELECT id, source_type, source, raw_content, created_at
        FROM items
        ORDER BY id
        """
    ).fetchall()

    for row in rows:
        preview = row["raw_content"] if args.all else row["raw_content"][:80]
        suffix = "" if args.all or len(row["raw_content"]) <= 80 else "..."
        print(
            f"#{row['id']} | {row['source_type']} | {row['source']} | {row['created_at']}"
        )
        print(f"  {preview}{suffix}\n")

    conn.close()


if __name__ == "__main__":
    main()
