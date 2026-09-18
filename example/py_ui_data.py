"""Backend-for-frontend data class, backed by the SQLite store.

The implementation stays on the server; Pytincture ships the browser a
generated stub with the same public methods. Keep secrets, database access and
file I/O in here -- never in browser modules.
"""
import json
from typing import Any, Literal, TypedDict

import store
from pytincture.dataclass import backend_for_frontend, bff_external

MAX_PAGE_SIZE = 100


class BookFields(TypedDict, total=False):
    title: str
    authors: str
    average_rating: float
    publication_date: str
    in_store: bool
    isbn13: int
    language_code: str
    num_pages: int
    ratings_count: int
    text_reviews_count: int
    publisher: str


class Book(BookFields):
    id: int


class BookPage(TypedDict):
    items: list[Book]
    page: int
    page_size: int
    total: int
    has_more: bool


class PingResponse(TypedDict):
    value: Any


class BookUpdated(TypedDict):
    ok: Literal[True]
    record: Book


class BookNotFound(TypedDict):
    ok: Literal[False]
    error: str


@backend_for_frontend
class py_ui_data:
    def dataset(self) -> str:
        """The books shown in the grid, as a JSON string."""
        return json.dumps(store.all_books())

    @bff_external
    def ping(self, value: Any) -> PingResponse:
        """Echo a value for API and load-profile checks."""
        return {"value": value}

    @bff_external
    def dataset_page(self, page: int = 1, page_size: int = MAX_PAGE_SIZE) -> BookPage:
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

    def update_book(self, book_id: int, fields: BookFields) -> BookUpdated | BookNotFound:
        """Persist edits to one book and return the stored row.

        Only whitelisted columns are written; `id` is never client-writable.
        """
        record = store.update_book(int(book_id), dict(fields or {}))
        if record is None:
            return {"ok": False, "error": "unknown book"}
        return {"ok": True, "record": record}
