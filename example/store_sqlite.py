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
_local = threading.local()
_total = None


def describe() -> str:
    return f"sqlite ({DB_PATH})"


def connect() -> sqlite3.Connection:
    """One connection per thread, reused for the life of that thread.

    The BFF runs calls on a worker pool, so a connection per call meant a
    connect plus two PRAGMAs on every request. sqlite3 connections are bound
    to their creating thread by default, which is exactly what thread-local
    storage gives us, and WAL lets those readers run concurrently.

    Callers keep using `with connect() as connection:` -- that commits or
    rolls back the transaction, it does not close the connection.
    """
    connection = getattr(_local, "connection", None)
    if connection is not None:
        return connection
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    _local.connection = connection
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
    """Row count, counted once.

    Every paginated call needs this, and COUNT(*) over the catalog was the
    single most expensive part of serving a page. The store has no insert or
    delete operation -- the catalog is fixed once initialise() has seeded it
    -- so counting on each call could only ever return the same number.
    """
    global _total
    initialise()
    if _total is None:
        with connect() as connection:
            _total = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    return _total


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
