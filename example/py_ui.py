"""
Example application using MainWindow subclass and layout management
with a sidebar, content area, and a grid using GridColumnConfig.
"""
import sys
from dhxpyt.layout import MainWindow
from dhxpyt.toolbar import ButtonConfig, ToolbarConfig  # Direct imports
from dhxpyt.sidebar import NavItemConfig, SeparatorConfig, SpacerConfig, SidebarConfig  # Direct imports
from dhxpyt.grid import GridConfig, GridColumnConfig  # Grid and GridColumnConfig
from dhxpyt.layout import LayoutConfig, CellConfig  # Direct imports

from py_ui_data import py_ui_data

class py_ui(MainWindow):
    def __init__(self):
        super().__init__()
        self.set_theme("dark")
        self.load_ui()

    def load_ui(self):
        # Add a toolbar to the pre-existing 'mainwindow_header'
        toolbar_buttons = [
            ButtonConfig(id="file", value="File", icon="mdi mdi-file"),
            ButtonConfig(id="edit", value="Edit", icon="mdi mdi-pencil"),
            ButtonConfig(id="help", value="Help", icon="mdi mdi-help-circle")
        ]
        toolbar_config = ToolbarConfig(data=toolbar_buttons)
        self.add_toolbar(id="mainwindow_header", toolbar_config=toolbar_config)

        # Create a layout for the body (main content area) with two columns: sidebar and main content
        body_layout_config = LayoutConfig(
            type="line",
            cols=[
                CellConfig(id="mainwindow_sidebar", width="20%"),  # Sidebar column
                CellConfig(id="mainwindow_content", width="80%")  # Content column
            ]
        )

        # Add the body layout to the pre-existing 'mainwindow' cell and capture the layout instance
        mw_body_layout = self.add_layout(id="mainwindow", layout_config=body_layout_config)

        # Sidebar items configuration
        sidebar_items = [
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
        sidebar_config = SidebarConfig(width="auto", data=sidebar_items)

        # Add the sidebar to the layout
        mw_body_layout.add_sidebar(id="mainwindow_sidebar", sidebar_config=sidebar_config)

        # Now, create a new layout within the 'mainwindow_content' cell with two rows:
        # One for the HTML content and another for the grid.
        content_layout_config = LayoutConfig(
            type="line",
            rows=[
                CellConfig(id="content_message", height="auto", width="100%"),  # Row for the HTML message
                CellConfig(id="content_grid", height="100%", width="100%")      # Row for the grid
            ]
        )

        # Add the new layout to 'mainwindow_content'
        content_layout = mw_body_layout.add_layout(id="mainwindow_content", layout_config=content_layout_config)

        # Add the HTML content to the top row (content_message)
        content_layout.attach_html(id="content_message", html="<h1  style='margin-left: 10px;'>Book Details and Ratings</h1>")

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

        data = py_ui_data().dataset()
        #print(data)

        # Grid configuration with columns
        grid_config = GridConfig(
            columns=grid_columns,
            height="400",
            data=data
        )

        # Add the grid to the bottom row (content_grid)
        self.content_grid = content_layout.add_grid(id="content_grid", grid_config=grid_config)
        self.content_grid.grid.data.parse(data)


if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service()
