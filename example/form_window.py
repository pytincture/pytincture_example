"""Modal window containing a book-details form.

The modal is built once and shown again for each book, so it does not dispose
on close. Saving goes through the BFF; the modal closes only when the write
lands, so a rejected save leaves the edit on screen with the error under it.
"""
import asyncio
import json

import js

from wapyt import Form, FormConfig, ModalConfig, ModalWindow

from book_fields import book_fields, form_to_record, record_to_form
from py_ui_data import py_ui_data


class FormExample:
    def __init__(self, languages=()):
        self.data = py_ui_data()
        self._record_id = None
        # Set by the caller to refresh the grid after a successful save.
        self.on_saved = None

        self.modal = ModalWindow(ModalConfig(title="Form Example", width=640, height=560))
        self.form = Form(
            FormConfig(
                fields=book_fields(languages),
                columns=2,
                submit_text="Save",
                cancel_text="Cancel",
            ),
            container=self.modal.body,
        )
        # on_submit fires only once client-side validation passes.
        self.form.on_submit(lambda values: asyncio.ensure_future(self._save(values)))
        self.form.on_cancel(lambda _values: self.modal.hide())

    def open(self, record=None):
        """Show the modal on `record`; omit it to load the first book."""
        self.form.clear_errors()
        self.modal.show()
        if record is not None:
            self.set_record(record)
        else:
            asyncio.ensure_future(self._load_first_record())

    def set_record(self, record):
        """Fill the form from a book record. Keys with no field are ignored."""
        self._record_id = (record or {}).get("id")
        self.form.set_values(record_to_form(record))

    async def _save(self, values):
        """Write the edited fields back through the BFF, then close on success."""
        if self._record_id is None:
            return
        self.form.set_busy(True)
        try:
            result = await self.data.update_book_async(self._record_id, form_to_record(values))
            if not result.get("ok"):
                # Leave the modal open so the edit is not lost on a failure.
                self.form.set_error(None, "Save rejected: " + str(result.get("error")))
                return
            if self.on_saved is not None:
                self.on_saved(result["record"])
            # Closing is the confirmation: the modal stays put on failure, so
            # it disappearing is what tells you the write landed.
            self.modal.hide()
        except Exception:
            import traceback
            js.console.error("save failed: " + traceback.format_exc())
            self.form.set_error(None, "Save failed; see the console.")
        finally:
            self.form.set_busy(False)

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
