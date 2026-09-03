"""Modal window containing a book-details form.

`Window` is a plain dhxpyt class -- unlike `Layout`/`MainWindow` it has no
`LoadUICaller` metaclass, so it does not call `load_ui()` for you. This class
calls it explicitly at the end of `__init__`.
"""
import asyncio
import json

import js
from pyodide.ffi import create_proxy

from dhxpyt.form import ButtonConfig, FormConfig, InputConfig, DatepickerConfig
from dhxpyt.window import Window, WindowConfig

from py_ui_data import py_ui_data


# Label beside the control rather than above it, with minimal padding.
COMPACT_FIELD = {
    "labelPosition": "left",
    "labelWidth": "130px",
    "padding": "2px",
}

# The seed dates are M/D/YYYY with no leading zeros ("9/16/2006").
# DatepickerConfig defaults to dateFormat="%d/%m/%y", which misreads them and
# writes the misreading back on save, so every save corrupted the date.
# %n and %j are the no-leading-zero month and day.
DATE_FORMAT = "%n/%j/%Y"

FIELDS = (
    ("title", "Title"),
    ("authors", "Authors"),
    ("average_rating", "Rating"),
    ("isbn13", "ISBN"),
    ("language_code", "Language"),
    ("num_pages", "Pages"),
    ("publisher", "Publisher"),
)


class FormExample(Window):
    def __init__(self, record=None):
        """`record` fills the form immediately; omit it to load the first book."""
        super().__init__(
            config=WindowConfig(
                title="Form Example",
                css="dhx_widget--bordered dhx_widget--bg_white",
                # Sized so all eight compact rows fit without scrolling and
                # the title value is not truncated.
                width=560,
                height=572,
                left=100,
                top=100,
                modal=True,
                resizable=True,
                movable=True,
                closable=True,
            )
        )
        self.data = py_ui_data()
        self.form = None
        self._initial_record = record
        self._record_id = None
        # Set by the caller to refresh the grid after a successful save.
        self.on_saved = None
        self.load_ui()

    def load_ui(self):
        fields = [
            InputConfig(id=field, label=label, **COMPACT_FIELD)
            for field, label in FIELDS
        ]
        fields.append(
            DatepickerConfig(
                id="publication_date",
                label="Publication Date",
                dateFormat=DATE_FORMAT,
                **COMPACT_FIELD,
            )
        )
        fields.append(
            # NB: the form's ButtonConfig takes `text`, not the toolbar
            # ButtonConfig's `value`.
            ButtonConfig(id="save", text="Save", submit=False, padding="6px")
        )

        # Window.attach(name, config) is the DHTMLX pattern for creating a
        # widget inside the window; get_widget() then returns the JS instance.
        self.show()
        # FormConfig(rows=...) renders controls; cols= produces an empty form.
        cfg = FormConfig(rows=fields).to_dict()
        self.attach("Form", js.JSON.parse(json.dumps(cfg)))
        self.form = self.get_widget()
        self.form.events.on("click", create_proxy(self._on_form_click))

        if self._initial_record is not None:
            self.set_record(self._initial_record)
        else:
            asyncio.ensure_future(self._load_first_record())

    def set_record(self, record):
        """Fill the form from a book record. Keys with no control are ignored."""
        self._record_id = (record or {}).get("id")
        self.form.setValue(js.JSON.parse(json.dumps(record)))

    def _on_form_click(self, name, event=None):
        if name == "save":
            asyncio.ensure_future(self._save())

    async def _save(self):
        """Write the edited fields back through the BFF, then close on success."""
        try:
            if self._record_id is None:
                return
            values = self.form.getValue().to_py()
            result = await self.data.update_book_async(self._record_id, values)
            if not result.get("ok"):
                # Leave the window open so the edit is not lost on a failure.
                js.console.error("save rejected: " + str(result.get("error")))
                return
            if self.on_saved is not None:
                self.on_saved(result["record"])
            # Closing is the confirmation: the window stays put on failure, so
            # it disappearing is what tells you the write landed.
            self.hide()
        except Exception:
            import traceback
            js.console.error("save failed: " + traceback.format_exc())

    async def _load_first_record(self):
        """Populate the form from the authenticated BFF."""
        try:
            raw = await self.data.dataset_async()
            records = json.loads(raw) if isinstance(raw, str) else raw
            if records:
                self.set_record(records[0])
        except Exception:
            import traceback
            js.console.error("form load failed: " + traceback.format_exc())
