import json
from functools import lru_cache
from pathlib import Path

from pytincture.dataclass import backend_for_frontend


MAX_PAGE_SIZE = 100
CATALOG_SIZE = 10_000


@lru_cache(maxsize=1)
def _source_records():
    return json.loads((Path(__file__).parent / "dataset.json").read_text())


@backend_for_frontend
class py_ui_data:
    def dataset(self):
        return open("dataset.json", "r").read()

    def ping(self, value):
        """Small authenticated BFF operation used by the load profile."""
        return {"value": value}

    def dataset_page(self, page=1, page_size=MAX_PAGE_SIZE):
        """Return a representative server-paginated grid response."""
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
        start = (page - 1) * page_size
        stop = min(start + page_size, CATALOG_SIZE)
        source = _source_records()
        items = []
        for index in range(start, stop):
            item = dict(source[index % len(source)])
            item["id"] = index + 1
            items.append(item)
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": CATALOG_SIZE,
            "has_more": stop < CATALOG_SIZE,
        }
