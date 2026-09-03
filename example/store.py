"""Data store for the example. SQLite by default; BriskDB as a drop-in demo.

    PYTINCTURE_EXAMPLE_STORE=sqlite    (default)
    PYTINCTURE_EXAMPLE_STORE=briskdb   pip install 'briskdb'

Both backends expose the same functions, so py_ui_data.py never knows which is
in use. Backend-specific setup and constraints live in the backend modules.
"""

from __future__ import annotations

import os

BACKEND = os.getenv("PYTINCTURE_EXAMPLE_STORE", "sqlite").strip().lower()

if BACKEND == "briskdb":
    import store_briskdb as _backend
elif BACKEND == "sqlite":
    import store_sqlite as _backend
else:
    raise RuntimeError(
        f"unknown PYTINCTURE_EXAMPLE_STORE {BACKEND!r}; expected 'sqlite' or 'briskdb'"
    )

describe = _backend.describe
initialise = _backend.initialise
all_books = _backend.all_books
page = _backend.page
total = _backend.total
get_book = _backend.get_book
update_book = _backend.update_book
