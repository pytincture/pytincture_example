"""
Example application using MainWindow subclass and layout management
with a collapsible sidebar, content area, and a Tabbar containing a grid, chart, and form.
"""
import json
import sys

from dhxpyt.layout import MainWindow
from dhxpyt.toolbar import ButtonConfig, ToolbarConfig, SeparatorConfig  # Direct imports
from dhxpyt.sidebar import NavItemConfig, SeparatorConfig, SpacerConfig, SidebarConfig  # Direct imports
from dhxpyt.grid import GridConfig, GridColumnConfig  # Grid and GridColumnConfig
from dhxpyt.chart import ChartConfig  # Chart and ChartConfig
from dhxpyt.layout import LayoutConfig, CellConfig  # Direct imports
from dhxpyt.tabbar import TabbarConfig, TabConfig  # Tabbar-related imports
from pyodide.ffi import create_proxy  # To handle JS signals
import js

from py_ui_data import py_ui_data  # Assuming this is pulling the book data

class py_ui(MainWindow):
    def __init__(self):
        super().__init__()
        self.set_theme("dark")
        self.sidebar_collapsed = False  # Track the sidebar state
        self.load_ui()

    def load_ui(self):
        # Add a toolbar to the pre-existing 'mainwindow_header'
        toolbar_buttons = [
            ButtonConfig(id="file", value="File", icon="mdi mdi-car-brake-hold"),
            ButtonConfig(id="edit", value="Edit", icon="mdi mdi-pencil"),
            SeparatorConfig(id="sep1"),
            ButtonConfig(id="help", value="Help", icon="mdi mdi-help-circle")
        ]
        toolbar_config = ToolbarConfig(data=toolbar_buttons)
        self.toolbar = self.add_toolbar(id="mainwindow_header", toolbar_config=toolbar_config)

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
            SeparatorConfig(),  # Separator
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
        self.sidebar.on_click(self.handle_toolbar_click)

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

        # Tabbar configuration with three tabs: Grid, Book Ratings Chart, Form
        tabbar_config = TabbarConfig(
            views=[
                TabConfig(id="tab1", tab="Grid View"),
                TabConfig(id="tab2", tab="Book Ratings Chart"),
                TabConfig(id="tab3", tab="Form View"),
                TabConfig(id="tab4", tab="Tab 4")
            ],
            activeTab="tab1"  # Set Grid View as the active tab by default
        )

        # Add the tabbar to the content_tabbar row
        self.tabbar = self.content_layout.add_tabbar(id="content_tabbar", tabbar_config=tabbar_config)

        # Grid columns configuration using GridColumnConfig
        grid_columns = [
            GridColumnConfig(width=300, id="title", header=[{"text": "Title"}]),
            GridColumnConfig(width=200, id="authors", header=[{"text": "Authors"}]),
            GridColumnConfig(width=80, id="average_rating", header=[{"text": "Rating"}]),
            GridColumnConfig(width=150, id="publication_date", header=[{"text": "Publication date"}]),
            GridColumnConfig(width=150, id="isbn13", header=[{"text": "ISBN"}]),
            GridColumnConfig(width=90, id="language_code", header=[{"text": "Language"}]),
            GridColumnConfig(width=90, id="num_pages", header=[{"text": "Pages"}]),
            GridColumnConfig(width=120, id="ratings_count", header=[{"text": "Rating count"}]),
            GridColumnConfig(width=100, id="text_reviews_count", header=[{"text": "Text reviews count"}]),
            GridColumnConfig(width=200, id="publisher", header=[{"text": "Publisher"}])
        ]

        # Fetching data from py_ui_data
        data = py_ui_data().dataset()

        # Grid configuration with columns
        grid_config = GridConfig(
            columns=grid_columns,
            data=data
        )

        # Attach the grid to the first tab (tab1) using tabbar.add_grid
        self.book_grid = self.tabbar.add_grid(id="tab1", grid_config=grid_config)

        # Assuming the structure of `data` matches the expected format
        book_chart_data = [
            {
                "title": book["title"],
                "average_rating": book["average_rating"],
                "ratings_count": book["ratings_count"]
            }
            for book in json.loads(data)
        ]

        # Book Ratings Chart configuration
        book_chart_config = ChartConfig(
            type="bar",
            series=[{
                "value": "average_rating",
                "text": "title"
            }],
            scales={},
            data=json.dumps(book_chart_data),
            css="dhx_widget--bg_white dhx_widget--bordered"
        )

        # Attach the book ratings chart to the second tab (tab2) using tabbar.add_chart
        self.tabbar.add_chart(id="tab2", chart_config=book_chart_config)

    def handle_toolbar_click(self, id, event):
        """Handle toolbar button clicks."""
        if id == "hamburger":
            self.toggle_sidebar()

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


if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service()
