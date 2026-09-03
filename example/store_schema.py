"""Shared schema, seed data and value rules for both store backends."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED_FILE = HERE / "dataset.json"

# The catalog is padded to this size by cycling the seed records, so
# dataset_page() exercises real pagination at the size the load profile expects.
# Rows 1..len(seed) are the seed in order, so a query limited to that range
# returns exactly the original dataset.
CATALOG_SIZE = 10_000

# Column affinities chosen to preserve the seed's JSON types on round-trip:
# average_rating stays a float, the counts stay ints, in_store stays a bool.
SCHEMA_TYPES = {
    "title": "TEXT",
    "authors": "TEXT",
    "average_rating": "REAL",
    "publication_date": "TEXT",
    "in_store": "INTEGER",
    "isbn13": "INTEGER",
    "language_code": "TEXT",
    "num_pages": "INTEGER",
    "ratings_count": "INTEGER",
    "text_reviews_count": "INTEGER",
    "publisher": "TEXT",
}
FIELDS = tuple(SCHEMA_TYPES)

# Neither engine has a boolean type; convert this one back on the way out.
BOOL_FIELDS = ("in_store",)

# Only these may be written by update_book(); `id` is never client-writable.
EDITABLE = frozenset(FIELDS)

CREATE_BOOKS = (
    "CREATE TABLE IF NOT EXISTS books (\n"
    "    id INTEGER PRIMARY KEY,\n"
    "    " + ",\n    ".join(f"{name} {kind}" for name, kind in SCHEMA_TYPES.items()) + "\n)"
)


def seed_records() -> list[dict]:
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


def distinct_count() -> int:
    """How many rows are the original seed rather than catalog padding."""
    return len(seed_records())


def catalog_rows() -> list[tuple]:
    """The full catalog as (id, *FIELDS) tuples, seed rows first and in order."""
    source = seed_records()
    return [
        (index + 1, *(source[index % len(source)].get(name) for name in FIELDS))
        for index in range(CATALOG_SIZE)
    ]


def normalise(record: dict) -> dict:
    """Restore Python types the engines cannot represent natively."""
    for name in BOOL_FIELDS:
        if record.get(name) is not None:
            record[name] = bool(record[name])
    return record


def editable_updates(fields: dict) -> dict:
    """Whitelist and coerce a client-supplied field mapping."""
    return {
        name: (int(value) if name in BOOL_FIELDS else value)
        for name, value in (fields or {}).items()
        if name in EDITABLE
    }
