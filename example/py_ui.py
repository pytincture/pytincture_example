"""
Example application using MainWindow subclass and layout management
with a collapsible sidebar, content area, a Tabbar containing a grid, chart,
calendar, and form.
"""
import asyncio
import json

import js
from pyodide.ffi import create_proxy

import widget  # declares __widgetset__/__version__ for the backend
from dhxpyt.layout import MainWindow
from dhxpyt.toolbar import (
    ButtonConfig,
    ToolbarConfig,
    SeparatorConfig as ToolbarSeparatorConfig,
    SpacerConfig as ToolbarSpacerConfig,
)
from dhxpyt.sidebar import NavItemConfig, SeparatorConfig as SidebarSeparatorConfig, SpacerConfig, SidebarConfig
from dhxpyt.grid import GridConfig, GridColumnConfig  # Grid and GridColumnConfig
from dhxpyt.calendar import CalendarConfig
from dhxpyt.chart import BarChartConfig
from dhxpyt.form import FormConfig, InputConfig, DatepickerConfig  # Importing form-related classes
from dhxpyt.layout import LayoutConfig, CellConfig  # Direct imports
from dhxpyt.tabbar import TabbarConfig, TabConfig  # Tabbar-related imports
from form_window import FormExample
from py_ui_data import py_ui_data  # Assuming this is pulling the book data


# dhx.setTheme() only writes data-dhx-theme on <html>; the suite stylesheet does
# the rest, so switching is live and no widget needs rebuilding.
THEMES = ("light", "dark")
THEME_STORAGE_KEY = "py_ui.theme"


# Label beside the control rather than above it, with minimal padding.
COMPACT_FIELD = {
    "labelPosition": "left",
    "labelWidth": "130px",
    "padding": "2px",
}


class py_ui(MainWindow):
    # Implement load_ui() only. dhxpyt's LoadUICaller metaclass calls it once the
    # instance is constructed; calling it from __init__ builds the UI twice.
    def load_ui(self):
        # A remembered choice wins; otherwise start from the OS preference.
        self.theme = self._stored_theme() or self._system_theme()
        self.set_theme(self.theme)
        self.sidebar_collapsed = False  # Track the sidebar state
        self.form_window = None  # Created lazily by the Reports sidebar item

        # Add a toolbar to the pre-existing 'mainwindow_header'
        toolbar_buttons = [
            ButtonConfig(id="file", value="File", icon="mdi mdi-car-brake-hold"),
            ButtonConfig(id="edit", value="Edit", icon="mdi mdi-pencil"),
            ToolbarSeparatorConfig(id="sep1"),
            ButtonConfig(id="help", value="Help", icon="mdi mdi-help-circle"),
            ToolbarSpacerConfig(),  # pushes the theme toggle to the right
            ButtonConfig(id="theme", **self._theme_button()),
        ]
        toolbar_config = ToolbarConfig(data=toolbar_buttons)
        self.toolbar = self.add_toolbar(id="mainwindow_header", toolbar_config=toolbar_config)
        self.toolbar.on_click(self.handle_toolbar_click)

        # Keep following the OS while no explicit choice has been made. The
        # proxy has to outlive load_ui(), or Pyodide frees the callback.
        self._system_media = js.window.matchMedia("(prefers-color-scheme: dark)")
        self._system_theme_proxy = create_proxy(self._on_system_theme_change)
        self._system_media.addEventListener("change", self._system_theme_proxy)

        # Create a layout for the body (main content area) with two columns: sidebar and main content
        body_layout_config = LayoutConfig(
            type="line",
            cols=[
                CellConfig(id="mainwindow_sidebar", width="auto"),  # Sidebar column
                CellConfig(id="mainwindow_content", width="100%")  # Content column
            ]
        )

        # Add the body layout to the pre-existing 'mainwindow' cell and capture the layout instance
        self.mw_body_layout = self.add_layout(id="mainwindow", layout_config=body_layout_config)

        # Sidebar items configuration
        sidebar_items = [
            NavItemConfig(id="hamburger", icon="mdi mdi-menu"),  # Hamburger button for collapsing/expanding
            NavItemConfig(id="dashboard", value="Dashboard", icon="mdi mdi-view-dashboard"),
            NavItemConfig(id="statistics", value="Statistics", icon="mdi mdi-chart-line"),
            NavItemConfig(id="reports", value="Reports", icon="mdi mdi-file-chart"),
            SidebarSeparatorConfig(),  # Separator
            NavItemConfig(id="posts", value="Posts", icon="mdi mdi-square-edit-outline", items=[
                NavItemConfig(id="addPost", value="New Post", icon="mdi mdi-plus"),
                NavItemConfig(id="allPost", value="Posts", icon="mdi mdi-view-list"),
                NavItemConfig(id="categoryPost", value="Category", icon="mdi mdi-tag")
            ]),
            NavItemConfig(id="pages", value="Pages", icon="mdi mdi-file-outline", items=[
                NavItemConfig(id="addPage", value="New Page", icon="mdi mdi-plus"),
                NavItemConfig(id="allPage", value="Pages", icon="mdi mdi-view-list"),
                NavItemConfig(id="categoryPages", value="Category", icon="mdi mdi-tag")
            ]),
            NavItemConfig(id="messages", value="Messages", icon="mdi mdi-email-mark-as-unread", count=18),
            NavItemConfig(id="media", value="Media", icon="mdi mdi-folder-multiple-image"),
            NavItemConfig(id="links", value="Links", icon="mdi mdi-link"),
            NavItemConfig(id="comments", value="Comments", icon="mdi mdi-comment-multiple-outline", count="118", countColor="primary", items=[
                NavItemConfig(id="myComments", value="My Comments", icon="mdi mdi-account", count=15),
                NavItemConfig(id="allComments", value="All Comments", icon="mdi mdi-comment-multiple-outline", count=103, countColor="primary")
            ]),
            SpacerConfig(),  # Spacer
            NavItemConfig(id="notification", value="Notification", icon="mdi mdi-bell", count=25, countColor="primary"),
            NavItemConfig(id="configuration", value="Configuration", icon="mdi mdi-settings", items=[
                NavItemConfig(id="myAccount", value="My Account", icon="mdi mdi-account-settings"),
                NavItemConfig(id="general", value="General Configuration", icon="mdi mdi-tune")
            ])
        ]

        # Sidebar configuration with width and the items
        sidebar_config = SidebarConfig(data=sidebar_items)

        # Add the sidebar to the layout
        self.sidebar = self.mw_body_layout.add_sidebar(id="mainwindow_sidebar", sidebar_config=sidebar_config)

        # Add event to the hamburger button to toggle the sidebar
        self.sidebar.on_click(self.handle_sidebar_click)

        # Now, create a new layout within the 'mainwindow_content' cell with two rows:
        # One for the HTML content and another for the tabbed content area.
        content_layout_config = LayoutConfig(
            type="line",
            rows=[
                CellConfig(id="content_message", height="auto"),  # Row for the HTML message
                CellConfig(id="content_tabbar", height="100%")      # Row for the tabbed area
            ]
        )

        # Add the new layout to 'mainwindow_content'
        self.content_layout = self.mw_body_layout.add_layout(id="mainwindow_content", layout_config=content_layout_config)

        # Add the HTML content to the top row (content_message)
        self.content_layout.attach_html(id="content_message", html="<h1 style='margin-left: 10px;'>Book Details and Ratings</h1>")

        # Tabbar configuration with four tabs: Grid, Book Ratings Chart, Form, Calendar
        tabbar_config = TabbarConfig(
            views=[
                TabConfig(id="tab1", tab="Grid View"),
                TabConfig(id="tab2", tab="Book Ratings Chart"),
                TabConfig(id="tab3", tab="Form View"),
                TabConfig(id="tab4", tab="Calendar View")
            ],
            activeTab="tab1"  # Set Grid View as the active tab by default
        )

        # Add the tabbar to the content_tabbar row
        self.tabbar = self.content_layout.add_tabbar(id="content_tabbar", tabbar_config=tabbar_config)

        # Grid columns. The second header row is a per-column "inputFilter",
        # which DHTMLX renders as a text box under the column title and applies
        # as a substring match while you type.
        grid_columns = [
            GridColumnConfig(
                width=width,
                id=field,
                header=[{"text": label}, {"content": "inputFilter"}],
            )
            for field, label, width in (
                ("title", "Title", 300),
                ("authors", "Authors", 200),
                ("average_rating", "Rating", 80),
                ("publication_date", "Publication date", 150),
                ("isbn13", "ISBN", 150),
                ("language_code", "Language", 90),
                ("num_pages", "Pages", 90),
                ("ratings_count", "Rating count", 120),
                ("text_reviews_count", "Text reviews count", 100),
                ("publisher", "Publisher", 200),
            )
        ]

        # Grid configuration with columns (data loaded asynchronously after init)
        grid_config = GridConfig(columns=grid_columns)

        # Attach the grid to the first tab (tab1) using tabbar.add_grid
        self.book_grid = self.tabbar.add_grid(id="tab1", grid_config=grid_config)

        # Double-clicking a row opens that book in the modal form.
        self.book_grid.on_cell_dbl_click(self.handle_grid_dbl_click)

        # Both tab1 and tab2 are filled from the one dataset call below.
        self.books = []
        self.book_chart = None
        asyncio.ensure_future(self._load_dataset())

        # Calendar configuration
        calendar_config = CalendarConfig(width="50%")
        self.cal = self.tabbar.add_calendar(id="tab4", calendar_config=calendar_config)

        # Add a form for the book details in tab3. Labels sit to the left of
        # each control with tight padding, so the whole record fits without
        # scrolling instead of one stacked label+input pair per row.
        book_fields = [
            ("title", "Title"),
            ("authors", "Authors"),
            ("average_rating", "Rating"),
            ("isbn13", "ISBN"),
            ("language_code", "Language"),
            ("num_pages", "Pages"),
            ("ratings_count", "Rating Count"),
            ("text_reviews_count", "Text Reviews Count"),
            ("publisher", "Publisher"),
        ]
        form_fields = [
            InputConfig(id=field, label=label, **COMPACT_FIELD)
            for field, label in book_fields
        ]
        form_fields.insert(
            3,
            DatepickerConfig(
                id="publication_date", label="Publication Date", **COMPACT_FIELD
            ),
        )

        # rows= renders the controls; cols= builds an empty form.
        form_config = FormConfig(rows=form_fields)

        # Attach the form to the third tab (tab3) using tabbar.add_form
        self.book_form = self.tabbar.add_form(id="tab3", form_config=form_config)

    async def _load_dataset(self):
        """Fill the grid (tab1) and build the ratings chart (tab2)."""
        # asyncio.ensure_future() swallows exceptions from this coroutine, so
        # report them explicitly rather than failing silently.
        try:
            # The generated stub exposes both dataset() (blocking XHR) and
            # dataset_async(); only the latter is awaitable.
            raw = await py_ui_data().dataset_async()
            self.books = json.loads(raw) if isinstance(raw, str) else raw
            # dhxpyt's Grid wrapper has no data API; reach the underlying widget.
            self.book_grid.grid.data.parse(js.JSON.parse(json.dumps(self.books)))
            self._build_chart()
        except Exception:
            import traceback
            js.console.error("dataset load failed: " + traceback.format_exc())

    def _chart_rows(self):
        """The ten most-rated books, titles trimmed so the axis stays legible."""
        top_rated = sorted(
            self.books, key=lambda book: book.get("ratings_count") or 0, reverse=True
        )[:10]
        return [
            {
                "title": (book.get("title") or "")[:24],
                "average_rating": book.get("average_rating") or 0,
            }
            for book in top_rated
        ]

    def _build_chart(self):
        """Build (or rebuild) the ratings chart on tab2.

        Chart.__init__ hands config.to_dict() to dhx through JSON, so data=
        and the derived scale are delivered the way the library expects.
        Rebuilding rather than re-parsing keeps one code path and lets the
        axis follow an edited rating. `css` gives the smoke test a selector
        that does not depend on dhx internals.
        """
        rows = self._chart_rows()
        # These books all rate within a few tenths of each other, so a 0-5
        # axis would draw ten near-identical bars. Fit the axis to the data,
        # padded, and clamped to the range a rating can actually take.
        ratings = [row["average_rating"] for row in rows] or [0]
        low = max(0.0, round(min(ratings) - 0.25, 1))
        high = min(5.0, round(max(ratings) + 0.25, 1))

        if self.book_chart is not None:
            self.book_chart.destructor()
        self.book_chart = self.tabbar.add_chart(
            id="tab2",
            chart_config=BarChartConfig(
                series=[
                    {"id": "rating", "value": "average_rating", "fill": "#4a90d9"}
                ],
                scales={
                    "bottom": {"text": "title"},
                    "left": {"min": low, "max": high},
                },
                data=rows,
                css="book-ratings-chart",
            ),
        )

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
            return {"value": "Light", "icon": "mdi mdi-white-balance-sunny"}
        return {"value": "Dark", "icon": "mdi mdi-weather-night"}

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
        self.toolbar.update_item("theme", self._theme_button())

    def _on_system_theme_change(self, event):
        # An explicit choice pins the mode; otherwise track the OS.
        if self._stored_theme() is None:
            self.set_mode("dark" if event.matches else "light", remember=False)

    def handle_toolbar_click(self, id, event):
        """Handle toolbar button clicks."""
        if id == "theme":
            self.set_mode("light" if self.theme == "dark" else "dark")

    def handle_sidebar_click(self, id, event):
        """Handle sidebar item clicks."""
        if id == "hamburger":
            self.toggle_sidebar()
        elif id == "reports":
            self.show_report_form()

    def handle_grid_dbl_click(self, row, column, event):
        """Open the modal on the double-clicked book."""
        self.show_report_form(record=row)

    def show_report_form(self, record=None):
        """Open the book-details modal, reusing the window across opens."""
        if self.form_window is None:
            # FormExample.load_ui() builds, attaches and shows the window.
            self.form_window = FormExample(record=record)
            self.form_window.on_saved = self.apply_saved_record
            return
        self.form_window.show()
        if record is not None:
            self.form_window.set_record(record)

    def apply_saved_record(self, record):
        """Reflect a saved book back into the grid row it came from."""
        self.book_grid.grid.data.update(
            record["id"], js.JSON.parse(json.dumps(record))
        )
        # Keep tab2 consistent with the edit: a changed rating or rating count
        # can reorder the chart and move its axis, so rebuild it.
        for index, book in enumerate(self.books):
            if book.get("id") == record["id"]:
                self.books[index] = record
                break
        if self.book_chart is not None:
            self._build_chart()

    def toggle_sidebar(self, event=None):
        """Toggle the sidebar collapse/expand state."""
        if self.sidebar_collapsed:
            # Expand the sidebar (show text)
            self.sidebar.toggle()
            self.sidebar_collapsed = False
        else:
            # Collapse the sidebar (hide text, show only icons)
            self.sidebar.toggle()
            self.sidebar_collapsed = True
