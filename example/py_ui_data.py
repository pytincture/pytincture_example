"""Backend-for-frontend data class, backed by the SQLite store.

The implementation stays on the server; Pytincture ships the browser a
generated stub with the same public methods. Keep secrets, database access and
file I/O in here -- never in browser modules.
"""
import json

import store
from pytincture.dataclass import backend_for_frontend

MAX_PAGE_SIZE = 100


@backend_for_frontend
class py_ui_data:
    def dataset(self):
        """The books shown in the grid, as a JSON string."""
        return json.dumps(store.all_books())

    def ping(self, value):
        """Small authenticated BFF operation used by the load profile."""
        return {"value": value}

    def dataset_page(self, page=1, page_size=MAX_PAGE_SIZE):
        """A server-paginated grid response, read with real LIMIT/OFFSET."""
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
        offset = (page - 1) * page_size
        total = store.total()
        items = store.page(offset, page_size)
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": offset + len(items) < total,
        }

    def update_book(self, book_id, fields):
        """Persist edits to one book and return the stored row.

        Only whitelisted columns are written; `id` is never client-writable.
        """
        record = store.update_book(int(book_id), dict(fields or {}))
        if record is None:
            return {"ok": False, "error": "unknown book"}
        return {"ok": True, "record": record}
