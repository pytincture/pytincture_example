"""The Media tab: readings in a docked audio bar, and a captioned film clip.

Runs in the browser. Two wapyt MediaPlayers share one exclusive group, so
starting the film pauses the reading and the other way round:

* the readings play in an audio bar docked to the foot of the window. It is
  mounted on <body>, outside the tabs, so it keeps playing while you go back
  to the grid;
* the film clip plays in place, with a WebVTT caption track.

The library (titles and URLs) comes from the BFF; the files themselves come
from the authenticated route in media_library.py.
"""
import js

from wapyt import (
    ColumnConfig,
    DataTable,
    DataTableConfig,
    MediaAction,
    MediaItem,
    MediaPlayer,
    MediaPlayerConfig,
    MediaTextTrack,
)

from py_ui_data import py_ui_data

# Players sharing a group pause one another.
GROUP = "example-media"

# TabWidget has no add_* helpers and a Layout cannot mount in a tab, so the
# tab gets plain markup and the widgets mount on the elements inside it.
MEDIA_TAB_HTML = """
<div class="example-media" style="display:flex; flex-wrap:wrap; gap:24px;
     padding:12px 16px; height:100%; box-sizing:border-box; overflow:auto;">
  <section style="flex:1 1 320px; min-width:0; display:flex; flex-direction:column;">
    <h2 style="margin:0 0 4px;">Readings</h2>
    <p style="margin:0 0 12px;">Pick a reading. It plays in the bar at the foot
      of the window and keeps playing while you use the other tabs.</p>
    <div id="example-media-readings" style="flex:1 1 auto; min-height:180px;"></div>
    <p style="margin:12px 0 0; font-size:12px; opacity:0.75;">Excerpts from
      LibriVox recordings, which are in the public domain.</p>
  </section>
  <section style="flex:1 1 360px; max-width:640px; min-width:0;">
    <h2 style="margin:0 0 4px;">Film clip</h2>
    <p style="margin:0 0 12px;">Twenty seconds, with captions.</p>
    <div id="example-media-film" style="aspect-ratio:16 / 9; width:100%;"></div>
    <p style="margin:12px 0 0; font-size:12px; opacity:0.75;">Big Buck Bunny,
      &copy; 2008 Blender Foundation, www.bigbuckbunny.org, CC BY 3.0.</p>
  </section>
</div>
"""


class MediaView:
    def __init__(self, tabs, tab_id="media"):
        tabs.attach_html(tab_id, MEDIA_TAB_HTML)
        self.readings = []
        self.liked = set()

        self.table = DataTable(DataTableConfig(
            columns=[
                ColumnConfig(id="title", header="Title", width=230),
                ColumnConfig(id="author", header="Author", width=160),
                ColumnConfig(id="length", header="Length", width=70, align="right"),
            ],
            id_field="id",
            selection="single",
            loading_text="Loading readings...",
        ), root="#example-media-readings")
        self.table.set_busy(True)
        self.table.on_select(self._on_select)

        self.film = MediaPlayer(MediaPlayerConfig(
            mode="video",
            group=GROUP,
            aria_label="Film clip",
        ), root="#example-media-film")

        # The dock lives on <body>: nothing the app re-renders can take it down.
        dock = js.document.createElement("div")
        js.document.body.appendChild(dock)
        self.audio = MediaPlayer(MediaPlayerConfig(
            mode="audio",
            dock="bottom",
            group=GROUP,
            aria_label="Readings",
            # A button of the app's own, beside the standard controls.
            actions=[MediaAction("like", "mdi-heart-outline", "Like", pressed=False)],
        ), container=dock)
        self.audio.on_change(self._on_change)
        self.audio.on_action(self._on_action)

    async def load(self):
        """Fetch the library from the BFF and fill both players."""
        try:
            library = await py_ui_data().media_library_async()
            self.readings = [item for item in library if item["kind"] == "audio"]
            self.table.set_rows(self.readings)
            films = [item for item in library if item["kind"] == "video"]
            self.film.load([
                MediaItem(
                    film["src"],
                    title=film["title"],
                    subtitle=film["author"],
                    poster=film["poster"],
                    text_tracks=[MediaTextTrack(film["captions"], "English", "en", default=True)],
                )
                for film in films
            ], autoplay=False)
        except Exception:
            import traceback
            js.console.error("media library load failed: " + traceback.format_exc())
        finally:
            self.table.set_busy(False)

    def _items(self):
        # `data` comes back in every event about the item, so no handler has
        # to map a queue index back to a reading.
        return [
            MediaItem(
                reading["src"],
                title=reading["title"],
                subtitle=reading["author"],
                album=reading["album"],
                kind="audio",
                data={"id": reading["id"]},
            )
            for reading in self.readings
        ]

    def _on_select(self, payload):
        rows = payload.get("rows") or []
        if not rows:
            return
        index = next(
            (i for i, reading in enumerate(self.readings) if reading["id"] == rows[0]["id"]),
            None,
        )
        if index is None:
            return
        state = self.audio.state()
        if not state.get("count"):
            # The first pick queues every reading, so Next and shuffle work.
            self.audio.load(self._items(), start_index=index, autoplay=True)
        elif state.get("index") != index:
            self.audio.play_index(index)
        # Otherwise the selection only followed the player (see _on_change).

    def _on_change(self, event):
        """Keep the table and the Like button on the reading now playing."""
        reading_id = (event.get("data") or {}).get("id")
        if reading_id is None:
            return
        self.table.select(reading_id)
        self._show_liked(reading_id)

    def _on_action(self, event):
        reading_id = (event.get("data") or {}).get("id")
        if event.get("action") != "like" or reading_id is None:
            return
        # symmetric_difference_update toggles membership.
        self.liked ^= {reading_id}
        self._show_liked(reading_id)

    def _show_liked(self, reading_id):
        liked = reading_id in self.liked
        self.audio.set_action(
            "like",
            pressed=liked,
            icon="mdi-heart" if liked else "mdi-heart-outline",
            label="Liked" if liked else "Like",
        )
