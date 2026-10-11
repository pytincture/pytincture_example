"""The demo media library: what is in it, and the route that serves it.

Server-side only. Pytincture ships Python modules to the browser and nothing
else, so the clips in `media/` need a route of their own. The page's
Content-Security-Policy has no `media-src`, which leaves `default-src 'self'`
in charge: media must come from this origin, as plain files. HLS (it needs
`blob:`) and a CDN on another origin are both refused by that policy.

The clips are short excerpts, small enough to live in the repository:

* Readings from LibriVox recordings, which are in the public domain.
* Twenty seconds of Big Buck Bunny, (c) 2008 Blender Foundation,
  www.bigbuckbunny.org, licensed CC BY 3.0. The captions are ours.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

MEDIA_DIR = Path(__file__).resolve().parent / "media"
# Namespaced so it can never collide with Pytincture's /{application}/... routes.
MEDIA_URL = "/example-media"

LIBRIVOX = "LibriVox (public domain)"

_READINGS = (
    ("pride-and-prejudice", "Pride and Prejudice", "Jane Austen", "0:33"),
    ("alice-in-wonderland", "Alice's Adventures in Wonderland", "Lewis Carroll", "0:32"),
    ("a-scandal-in-bohemia", "A Scandal in Bohemia", "Arthur Conan Doyle", "0:33"),
    ("moby-dick", "Moby-Dick", "Herman Melville", "0:37"),
)

_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".jpg": "image/jpeg",
    ".vtt": "text/vtt; charset=utf-8",
}


def _url(name):
    return f"{MEDIA_URL}/{name}"


def library():
    """Every item the Media tab offers, with the URLs to fetch it from."""
    items = [
        {
            "id": slug,
            "kind": "audio",
            "title": title,
            "author": author,
            "album": LIBRIVOX,
            "length": length,
            "src": _url(f"{slug}.mp3"),
        }
        for slug, title, author, length in _READINGS
    ]
    items.append({
        "id": "big-buck-bunny",
        "kind": "video",
        "title": "Big Buck Bunny",
        "author": "Blender Foundation",
        "length": "0:20",
        "src": _url("big-buck-bunny.mp4"),
        "poster": _url("big-buck-bunny.jpg"),
        "captions": _url("big-buck-bunny.en.vtt"),
    })
    return items


# The files that may be served, fixed when the module loads. A request names
# one of these or gets a 404; the name never becomes part of a path.
_FILES = {
    path.name: path
    for path in sorted(MEDIA_DIR.iterdir())
    if path.is_file() and path.suffix in _CONTENT_TYPES
}

router = APIRouter(prefix=MEDIA_URL)


@router.get("/{name}", include_in_schema=False)
def media_file(name: str, request: Request):
    """One clip, for a signed-in user.

    A plain route never passes through the BFF handler, so it checks the
    session itself. FileResponse answers Range requests, which is what lets
    the player seek without downloading the whole file.
    """
    session = request.scope.get("session") or {}
    if not session.get("user"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    path = _FILES.get(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Unknown media file")
    return FileResponse(
        path,
        media_type=_CONTENT_TYPES[path.suffix],
        headers={"Cache-Control": "private, max-age=3600"},
    )
