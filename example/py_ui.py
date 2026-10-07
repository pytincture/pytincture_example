"""
Example application using a wapyt MainWindow subclass and layout management:
a collapsible sidebar, a toolbar with a light/dark toggle, and a tab widget
holding the book grid and a form that mirrors the selected book.
"""
import asyncio
import json

import js
from pyodide.ffi import create_proxy

import widget  # declares __widgetset__/__version__ for the backend
from wapyt import (
    CellConfig,
    ColumnConfig,
    DataTable,
    DataTableConfig,
    Form,
    FormConfig,
    LayoutConfig,
    MainWindow,
    SelectOption,
    SidebarConfig,
    SidebarItem,
    SidebarSeparator,
    SidebarSpacer,
    TabConfig,
    TableAction,
    TabWidgetConfig,
    ToolbarButton,
    ToolbarConfig,
    ToolbarSeparator,
    ToolbarSpacer,
)
from book_fields import book_fields, record_to_form
from form_window import FormExample
from py_ui_data import py_ui_data

# Pytincture only auto-detects dhxpyt's MainWindow; name the wapyt one.
APP_ENTRYPOINT = "py_ui"


# set_theme() only writes data-wapyt-theme on <html>; the stylesheet does the
# rest, so switching is live and no widget needs rebuilding.
THEMES = ("light", "dark")
THEME_STORAGE_KEY = "py_ui.theme"


class py_ui(MainWindow):
    # Implement load_ui() only. wapyt's LoadUICaller metaclass calls it once the
    # instance is constructed; calling it from __init__ builds the UI twice.
    def load_ui(self):
        # A remembered choice wins; otherwise start from the OS preference.
        self.theme = self._stored_theme() or self._system_theme()
        self.set_theme(self.theme)
        self.form_window = None  # Created lazily by the Reports sidebar item

        # The default MainWindow layout has a 'mainwindow_header' row for this.
        self.toolbar = self.add_toolbar("mainwindow_header", ToolbarConfig(items=[
            ToolbarButton("file", "File", "mdi-car-brake-hold"),
            ToolbarButton("edit", "Edit", "mdi-pencil"),
            ToolbarSeparator(),
            ToolbarButton("help", "Help", "mdi-help-circle"),
            ToolbarSpacer(),  # pushes the theme toggle to the right
            ToolbarButton("theme", **self._theme_button()),
        ]))
        self.toolbar.on_click(self.handle_toolbar_click)

        # Keep following the OS while no explicit choice has been made. The
        # proxy has to outlive load_ui(), or Pyodide frees the callback.
        self._system_media = js.window.matchMedia("(prefers-color-scheme: dark)")
        self._system_theme_proxy = create_proxy(self._on_system_theme_change)
        self._system_media.addEventListener("change", self._system_theme_proxy)

        # The body (the 'mainwindow' row) splits into the sidebar and content.
        self.mw_body_layout = self.add_layout("mainwindow", LayoutConfig(cols=[
            CellConfig(id="mainwindow_sidebar", width="auto"),
            CellConfig(id="mainwindow_content", grow=1),
        ]))

        # Groups expand in place, or open as a flyout when the rail is
        # collapsed; the built-in button collapses it, so no hamburger item.
        self.sidebar = self.mw_body_layout.add_sidebar("mainwindow_sidebar", SidebarConfig(items=[
            SidebarItem("dashboard", "Dashboard", "mdi-view-dashboard"),
            SidebarItem("statistics", "Statistics", "mdi-chart-line"),
            SidebarItem("reports", "Reports", "mdi-file-chart"),
            SidebarSeparator(),
            SidebarItem("posts", "Posts", "mdi-square-edit-outline", items=[
                SidebarItem("addPost", "New Post", "mdi-plus"),
                SidebarItem("allPost", "Posts", "mdi-view-list"),
                SidebarItem("categoryPost", "Category", "mdi-tag"),
            ]),
            SidebarItem("pages", "Pages", "mdi-file-outline", items=[
                SidebarItem("addPage", "New Page", "mdi-plus"),
                SidebarItem("allPage", "Pages", "mdi-view-list"),
                SidebarItem("categoryPages", "Category", "mdi-tag"),
            ]),
            SidebarItem("messages", "Messages", "mdi-email-mark-as-unread", badge=18),
            SidebarItem("media", "Media", "mdi-folder-multiple-image"),
            SidebarItem("links", "Links", "mdi-link"),
            SidebarItem("comments", "Comments", "mdi-comment-multiple-outline", badge=118, items=[
                SidebarItem("myComments", "My Comments", "mdi-account", badge=15),
                SidebarItem("allComments", "All Comments", "mdi-comment-multiple-outline", badge=103),
            ]),
            SidebarSpacer(),
            SidebarItem("notification", "Notification", "mdi-bell", badge=25),
            SidebarItem("configuration", "Configuration", "mdi-cog", items=[
                SidebarItem("myAccount", "My Account", "mdi-account-cog"),
                SidebarItem("general", "General Configuration", "mdi-tune"),
            ]),
        ]))
        self.sidebar.on_select(self.handle_sidebar_select)

        # The content column: a heading row above the tabs.
        self.content_layout = self.mw_body_layout.add_layout("mainwindow_content", LayoutConfig(rows=[
            CellConfig(id="content_message", height="auto"),
            CellConfig(id="content_tabs", grow=1),
        ]))
        self.content_layout.attach_html(
            "content_message", "<h1 style='margin-left: 10px;'>Book Details and Ratings</h1>"
        )

        self.tabs = self.content_layout.add_tabwidget("content_tabs", TabWidgetConfig(
            tabs=[
                TabConfig(id="grid", title="Grid View"),
                TabConfig(id="form", title="Form View"),
            ],
            active="grid",
        ))

        # TabWidget has no add_* helpers: widgets mount into a tab's panel.
        # One filter box above the table matches across every column. Rows are
        # filled once the dataset call below returns.
        self.book_grid = DataTable(DataTableConfig(
            columns=[
                ColumnConfig(id=field, header=label, width=width, align=align)
                for field, label, width, align in (
                    ("title", "Title", 300, None),
                    ("authors", "Authors", 200, None),
                    ("average_rating", "Rating", 80, "right"),
                    ("publication_date", "Publication date", 150, None),
                    ("isbn13", "ISBN", 150, None),
                    ("language_code", "Language", 90, None),
                    ("num_pages", "Pages", 90, "right"),
                    ("ratings_count", "Rating count", 120, "right"),
                    ("text_reviews_count", "Text reviews count", 100, "right"),
                    ("publisher", "Publisher", 200, None),
                )
            ],
            selection="single",
            filterable=True,
            filter_placeholder="Filter books...",
            loading_text="Loading books...",
            resizable_columns=True,
            # Right-click offers the edit action as a second affordance.
            context_actions=[TableAction("edit", "Edit", "mdi-pencil")],
        ), container=self._tab_host("grid"))
        self.book_grid.set_busy(True)
        # Selecting a row mirrors it into the Form View tab.
        self.book_grid.on_select(self.handle_grid_select)
        # Double-clicking a row opens that book in the modal form.
        self.book_grid.on_activate(lambda payload: self.show_report_form(payload["row"]))
        self.book_grid.on_action(self.handle_grid_action)

        # The Form View tab mirrors the selected book and has no save button;
        # edits are saved through the modal, which writes through the BFF.
        self.book_form = Form(FormConfig(
            fields=book_fields(),
            columns=2,
            # "" rather than None: FormConfig drops None values, which lets
            # the JS default ("Save") back in.
            submit_text="",
        ), container=self._tab_host("form"))

        self.books = []
        asyncio.ensure_future(self._load_dataset())

    def _tab_host(self, tab_id):
        """A full-size element inside a tab's panel, for a widget to mount on.

        Not the panel itself: a widget takes over the element it mounts on,
        including its display, and the panel's own display is what hides an
        inactive tab.
        """
        host = js.document.createElement("div")
        host.style.height = "100%"
        self.tabs.get_cell(tab_id).getContainer().appendChild(host)
        return host

    async def _load_dataset(self):
        """Fill the grid and the form's language options."""
        # asyncio.ensure_future() swallows exceptions from this coroutine, so
        # report them explicitly rather than failing silently.
        try:
            # The generated stub exposes both dataset() (blocking XHR) and
            # dataset_async(); only the latter is awaitable.
            raw = await py_ui_data().dataset_async()
            self.books = json.loads(raw) if isinstance(raw, str) else raw
            self.book_grid.set_rows(self.books)
            self._fill_language_options()
        except Exception:
            import traceback
            js.console.error("dataset load failed: " + traceback.format_exc())
        finally:
            self.book_grid.set_busy(False)

    def languages(self):
        """The catalog's language codes, as combo options."""
        codes = sorted({book.get("language_code") for book in self.books if book.get("language_code")})
        return [SelectOption(code) for code in codes]

    def _fill_language_options(self):
        self.book_form.set_field_options("language_code", self.languages())

    # ---- light / dark mode ------------------------------------------------

    def _stored_theme(self):
        """The theme the user last picked, or None to follow the OS."""
        try:
            stored = js.localStorage.getItem(THEME_STORAGE_KEY)
        except Exception:  # storage can be blocked or unavailable
            return None
        return stored if stored in THEMES else None

    def _system_theme(self):
        try:
            media = js.window.matchMedia("(prefers-color-scheme: dark)")
        except Exception:
            return "light"
        return "dark" if media.matches else "light"

    def _theme_button(self):
        """Label and icon for the mode the button switches *to*."""
        if self.theme == "dark":
            return {"label": "Light", "icon": "mdi-white-balance-sunny"}
        return {"label": "Dark", "icon": "mdi-weather-night"}

    def set_mode(self, theme, remember=True):
        """Switch the whole UI between 'light' and 'dark'."""
        if theme not in THEMES:
            return
        self.theme = theme
        self.set_theme(theme)
        if remember:
            try:
                js.localStorage.setItem(THEME_STORAGE_KEY, theme)
            except Exception:  # a blocked store must not break the toggle
                pass
        button = self._theme_button()
        self.toolbar.set_text("theme", button["label"])
        self.toolbar.set_icon("theme", button["icon"])

    def _on_system_theme_change(self, event):
        # An explicit choice pins the mode; otherwise track the OS.
        if self._stored_theme() is None:
            self.set_mode("dark" if event.matches else "light", remember=False)

    # ---- events -----------------------------------------------------------

    def handle_toolbar_click(self, payload):
        if payload["id"] == "theme":
            self.set_mode("light" if self.theme == "dark" else "dark")

    def handle_sidebar_select(self, payload):
        if payload["id"] == "reports":
            self.show_report_form()

    def handle_grid_select(self, payload):
        rows = payload.get("rows") or []
        if rows:
            self.show_record_in_form(rows[0])

    def handle_grid_action(self, payload):
        """Context-menu actions operate on the right-clicked row."""
        if payload["action"] == "edit" and payload.get("row"):
            self.show_report_form(payload["row"])

    def show_record_in_form(self, record):
        """Fill the Form View tab from a book record."""
        if not record:
            return
        try:
            self.book_form.set_values(record_to_form(record))
        except Exception:
            import traceback
            js.console.error("form fill failed: " + traceback.format_exc())

    def show_report_form(self, record=None):
        """Open the book-details modal, reusing it across opens."""
        if self.form_window is None:
            self.form_window = FormExample(languages=self.languages())
            self.form_window.on_saved = self.apply_saved_record
        self.form_window.open(record)

    def apply_saved_record(self, record):
        """Reflect a saved book back into the grid and the Form View tab."""
        for index, book in enumerate(self.books):
            if book.get("id") == record["id"]:
                self.books[index] = record
                break
        # set_rows keeps the filter, sort and selection.
        self.book_grid.set_rows(self.books)
        self.show_record_in_form(record)
