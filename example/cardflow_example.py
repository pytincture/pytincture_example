"""
Example application demonstrating the DHX CardFlow widget with pytincture.
This example shows a basic CardFlow implementation with sample task data.
"""
import json
import sys

from dhxpyt.layout import MainWindow, LayoutConfig, CellConfig
from dhxpyt.toolbar import ButtonConfig, ToolbarConfig, SeparatorConfig
from dhxpyt.cardflow import CardFlow, CardFlowConfig, CardFlowColumnConfig
from pyodide.ffi import create_proxy
import js

class cardflow_example(MainWindow):
    def __init__(self):
        super().__init__()
        self.set_theme("material")
        self.load_ui()

    def load_ui(self):
        # Add a toolbar to the pre-existing 'mainwindow_header'
        toolbar_buttons = [
            ButtonConfig(id="refresh", value="Refresh", icon="mdi mdi-refresh"),
            ButtonConfig(id="add", value="Add Card", icon="mdi mdi-plus"),
            SeparatorConfig(id="sep1"),
            ButtonConfig(id="help", value="Help", icon="mdi mdi-help-circle")
        ]
        toolbar_config = ToolbarConfig(data=toolbar_buttons)
        self.toolbar = self.add_toolbar(id="mainwindow_header", toolbar_config=toolbar_config)
        self.toolbar.on_click(self.handle_toolbar_click)

        # Create a layout for the body (main content area)
        body_layout_config = LayoutConfig(
            type="line",
            rows=[
                CellConfig(id="title_cell", height="auto"),
                CellConfig(id="cardflow_cell", height="100%")
            ]
        )

        # Add the body layout to the pre-existing 'mainwindow' cell
        self.body_layout = self.add_layout(id="mainwindow", layout_config=body_layout_config)
        
        # Add a title
        self.body_layout.attach_html(id="title_cell", html="<h1 style='margin: 20px;'>CardFlow Task Management Example</h1>")

        # Configure CardFlow columns
        cardflow_columns = [
            CardFlowColumnConfig(id="task", header="Task", width="250px"),
            CardFlowColumnConfig(id="assignee", header="Assignee", width="150px"),
            CardFlowColumnConfig(id="priority", header="Priority", width="100px"),
            CardFlowColumnConfig(id="deadline", header="Deadline", width="150px", dataType="date", dataFormat="%Y-%m-%d"),
            CardFlowColumnConfig(id="status", header="Status", width="120px"),
            CardFlowColumnConfig(id="comments", header="Comments", width="200px")
        ]

        # Sample data for the CardFlow
        cardflow_data = [
            {
                "id": "task1",
                "task": "Complete dashboard design",
                "assignee": "John Smith",
                "priority": "High",
                "deadline": "2023-12-15",
                "status": "In Progress",
                "comments": "Need to finalize color schemes"
            },
            {
                "id": "task2",
                "task": "Database migration",
                "assignee": "Sarah Johnson",
                "priority": "Critical",
                "deadline": "2023-11-30",
                "status": "Pending",
                "comments": "Waiting for server setup"
            },
            {
                "id": "task3",
                "task": "Fix login page bug",
                "assignee": "Michael Chen",
                "priority": "Medium",
                "deadline": "2023-12-05",
                "status": "In Progress",
                "comments": "Issue with password reset"
            },
            {
                "id": "task4",
                "task": "Update documentation",
                "assignee": "Emma Rodriguez",
                "priority": "Low",
                "deadline": "2023-12-20",
                "status": "Not Started",
                "comments": "Need to review API changes"
            },
            {
                "id": "task5",
                "task": "Performance optimization",
                "assignee": "David Lee",
                "priority": "High",
                "deadline": "2023-12-10",
                "status": "In Progress",
                "comments": "Query optimization needed"
            },
            {
                "id": "task6",
                "task": "User testing",
                "assignee": "Lisa Wang",
                "priority": "Medium",
                "deadline": "2023-12-18",
                "status": "Not Started",
                "comments": "Prepare test scenarios"
            },
            {
                "id": "task7",
                "task": "Security audit",
                "assignee": "James Wilson",
                "priority": "Critical",
                "deadline": "2023-12-01",
                "status": "Completed",
                "comments": "Vulnerabilities fixed"
            }
        ]

        # Option items for the cards
        option_items = [
            {"id": "edit", "value": "Edit", "icon": "mdi mdi-pencil"},
            {"id": "delete", "value": "Delete", "icon": "mdi mdi-delete"},
            {"id": "move", "value": "Move", "icon": "mdi mdi-arrow-right"}
        ]

        # CardFlow configuration with columns and data
        cardflow_config = CardFlowConfig(
            columns=cardflow_columns,
            data=cardflow_data,
            editable=True,
            group={"order": ["status"]},
            groupable=True,
            hideExpandCollapse=False,
            optionItems=option_items,
            sortDisabled=False,
            sortHeader="Tasks"
        )

        # Create the CardFlow and attach it to the layout
        self.cardflow = CardFlow(cardflow_config)
        self.body_layout.attach(id="cardflow_cell", widget=self.cardflow.cardflow)

        # Set up event handlers for the CardFlow
        self.cardflow.on_sort(create_proxy(self.handle_sort))
        self.cardflow.on_card_options(create_proxy(self.handle_card_options))
        self.cardflow.on_card_expand(create_proxy(self.handle_card_expand))
        self.cardflow.on_card_collapse(create_proxy(self.handle_card_collapse))

    def handle_toolbar_click(self, id, event):
        """Handle toolbar button clicks."""
        if id == "refresh":
            self.cardflow.update_header()
            js.alert("CardFlow refreshed!")
        elif id == "add":
            js.alert("Add card functionality would go here")
        elif id == "help":
            js.alert("CardFlow example help: This demonstrates the DHX CardFlow widget with sample task data.")

    def handle_sort(self, event):
        """Handle sort events in the CardFlow."""
        print(f"CardFlow sorted: {event}")

    def handle_card_options(self, id, option):
        """Handle card option button clicks."""
        print(f"Option clicked: {option} for card {id}")
        js.alert(f"Option clicked: {option} for card {id}")

    def handle_card_expand(self, id):
        """Handle card expand events."""
        print(f"Card expanded: {id}")
        # Example of adding a custom widget to an expanded card
        layout_config = LayoutConfig(
            type="line",
            rows=[
                CellConfig(id="expandedContent", height="100%")
            ]
        )
        
        # Add some HTML content to the expanded card
        html_content = f"""
        <div style="padding: 15px;">
            <h3>Task Details</h3>
            <p>This area can contain additional details, comments, or even other widgets.</p>
            <p>You could add forms, charts, or other components here.</p>
            <button onclick="alert('Action button clicked!')">Action Button</button>
        </div>
        """
        # Attach the HTML content to the card
        self.cardflow.attach_to_card_content(id, html_content)

    def handle_card_collapse(self, id):
        """Handle card collapse events."""
        print(f"Card collapsed: {id}")
        # Detach any content when card is collapsed
        self.cardflow.detach_from_card_content(id)

if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service() 