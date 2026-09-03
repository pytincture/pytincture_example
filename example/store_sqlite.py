"""SQLite backend (the default).

Needs no external service, adds no dependency beyond the standard library, and
keeps working under BFF_EXECUTION_MODE=isolated-process. WAL mode handles the
load profile's 250 concurrent sessions.

The database lives outside `modules_path`: that directory is packaged and
shipped to the browser, and Pytincture warns when it is writable
(`security.modules_path_writable`). Override with PYTINCTURE_EXAMPLE_DB.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

from store_schema import (
    CREATE_BOOKS,
    FIELDS,
    catalog_rows,
    distinct_count,
    editable_updates,
    normalise,
)

DB_PATH = Path(
    os.getenv("PYTINCTURE_EXAMPLE_DB", "/tmp/pytincture-example/books.db")
).resolve()

_init_lock = threading.Lock()
_initialised = False


def describe() -> str:
    return f"sqlite ({DB_PATH})"


def connect() -> sqlite3.Connection:
    """One short-lived connection per call; WAL makes that cheap and safe."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    return connection


def initialise() -> None:
    global _initialised
    if _initialised:
        return
    with _init_lock:
        if _initialised:
            return
        with connect() as connection:
            connection.execute(CREATE_BOOKS)
            existing = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
            if existing < len(catalog_rows()):
                columns = ", ".join(("id",) + FIELDS)
                placeholders = ", ".join("?" * (len(FIELDS) + 1))
                connection.executemany(
                    f"INSERT OR REPLACE INTO books ({columns}) VALUES ({placeholders})",
                    catalog_rows(),
                )
        _initialised = True


def _as_dicts(rows) -> list[dict]:
    return [normalise(dict(row)) for row in rows]


def all_books() -> list[dict]:
    initialise()
    with connect() as connection:
        return _as_dicts(
            connection.execute(
                "SELECT * FROM books WHERE id <= ? ORDER BY id", (distinct_count(),)
            ).fetchall()
        )


def page(offset: int, limit: int) -> list[dict]:
    initialise()
    with connect() as connection:
        return _as_dicts(
            connection.execute(
                "SELECT * FROM books ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        )


def total() -> int:
    initialise()
    with connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]


def get_book(book_id: int) -> dict | None:
    initialise()
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM books WHERE id = ?", (int(book_id),)
        ).fetchone()
    return normalise(dict(row)) if row else None


def update_book(book_id: int, fields: dict) -> dict | None:
    initialise()
    updates = editable_updates(fields)
    if not updates:
        return get_book(book_id)
    assignments = ", ".join(f"{name} = ?" for name in updates)
    with connect() as connection:
        connection.execute(
            f"UPDATE books SET {assignments} WHERE id = ?",
            (*updates.values(), int(book_id)),
        )
    return get_book(book_id)
