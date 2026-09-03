"""BriskDB backend (opt-in demo): PYTINCTURE_EXAMPLE_STORE=briskdb

BriskDB runs a sharded-SQLite engine in-process. Two of its constraints shape
this module, and both differ from the SQLite backend:

1. Sessions are shared, not per-call. Opening a session per BFF call raises
   `BusyError: shard N connection queue is full` under the load profile's 250
   concurrent sessions; one long-lived session handles the same load with no
   errors and roughly ten times the throughput.

2. Schema migration requires sole-process ownership. `initialise()` must run
   before any peer process opens the directory -- run.py calls it at startup.
   A peer attempting to migrate gets `BusyError: another BriskDB process has
   this data directory open`; ordinary reads and writes across processes are
   supported.

BriskDB is alpha software. SQLite remains the example's default.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

import briskdb

from store_schema import (
    CREATE_BOOKS,
    FIELDS,
    catalog_rows,
    distinct_count,
    editable_updates,
    normalise,
)

DATA_DIR = Path(
    os.getenv("PYTINCTURE_EXAMPLE_BRISKDB_DIR", "/tmp/pytincture-example/briskdb")
).resolve()
SHARDS = int(os.getenv("PYTINCTURE_EXAMPLE_BRISKDB_SHARDS", "4"))

# One table keyed by book id, so a single routing key is correct here. Sharding
# books across keys would make every read a cross-shard concern for no benefit.
ROUTING_KEY = "books"

_lock = threading.Lock()
_db = None
_session = None
_total = None


def describe() -> str:
    return f"briskdb {getattr(briskdb, '__version__', '?')} ({DATA_DIR}, shards={SHARDS})"


def session():
    """The process-wide session. Safe to share across threads."""
    global _db, _session
    if _session is not None:
        return _session
    with _lock:
        if _session is None:
            DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
            _db = briskdb.open(str(DATA_DIR), shards=SHARDS)
            _session = _db.session(routing_key=ROUTING_KEY)
    return _session


def _seeded(handle) -> bool:
    try:
        return handle.query("SELECT COUNT(*) FROM books")["rows"][0][0] >= len(
            catalog_rows()
        )
    except Exception:
        return False


def initialise() -> None:
    """Create and populate the catalog. Must run before peers open the directory."""
    handle = session()
    if _seeded(handle):
        return
    with _lock:
        if _seeded(handle):
            return
        try:
            handle.migrate(CREATE_BOOKS)
        except Exception:
            # A peer created the schema first; that is fine as long as it exists.
            if not _seeded(handle):
                raise
            return
        columns = ", ".join(("id",) + FIELDS)
        placeholders = ", ".join(f"?{i + 1}" for i in range(len(FIELDS) + 1))
        insert = f"INSERT OR REPLACE INTO books ({columns}) VALUES ({placeholders})"
        for row in catalog_rows():
            handle.execute(insert, list(row))


def _as_dicts(result) -> list[dict]:
    names = [column["name"] for column in result["columns"]]
    return [normalise(dict(zip(names, row))) for row in result["rows"]]


def all_books() -> list[dict]:
    initialise()
    return _as_dicts(
        session().query(
            "SELECT * FROM books WHERE id <= ?1 ORDER BY id", [distinct_count()]
        )
    )


def page(offset: int, limit: int) -> list[dict]:
    initialise()
    return _as_dicts(
        session().query(
            "SELECT * FROM books ORDER BY id LIMIT ?1 OFFSET ?2", [limit, offset]
        )
    )


def total() -> int:
    """Row count, counted once -- see the note in store_sqlite.total()."""
    global _total
    initialise()
    if _total is None:
        _total = session().query("SELECT COUNT(*) FROM books")["rows"][0][0]
    return _total


def get_book(book_id: int) -> dict | None:
    initialise()
    rows = _as_dicts(
        session().query("SELECT * FROM books WHERE id = ?1", [int(book_id)])
    )
    return rows[0] if rows else None


def update_book(book_id: int, fields: dict) -> dict | None:
    initialise()
    updates = editable_updates(fields)
    if not updates:
        return get_book(book_id)
    assignments = ", ".join(f"{name} = ?{i + 1}" for i, name in enumerate(updates))
    session().execute(
        f"UPDATE books SET {assignments} WHERE id = ?{len(updates) + 1}",
        [*updates.values(), int(book_id)],
    )
    return get_book(book_id)
