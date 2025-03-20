"""
Example application demonstrating the DHX CardFlow widget with pytincture.
This example shows a basic CardFlow implementation with sample task data.
"""
import json
import sys

from dhxpyt.layout import MainWindow, LayoutConfig, CellConfig, Layout
from dhxpyt.toolbar import ButtonConfig, ToolbarConfig, SeparatorConfig
from dhxpyt.tabbar import TabbarConfig, TabConfig
from dhxpyt.cardflow import CardFlowConfig, CardFlowColumnConfig
from pyodide.ffi import create_proxy
import js

class cardflow_recon(MainWindow):
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
                CellConfig(id="cardflow_container", height="100%")
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
            }
        ]

        # Option items for the cards
        option_items = [
            {"id": "edit", "value": "Edit", "icon": "mdi mdi-pencil"},
            {"id": "delete", "value": "Delete", "icon": "mdi mdi-delete"},
            {"id": "move", "value": "Move", "icon": "mdi mdi-arrow-right"}
        ]

        try:
            # Create CardFlow configuration
            cardflow_config = CardFlowConfig(
                columns=cardflow_columns,
                data=cardflow_data,
                editable=True,
                groupable=True,
                hideExpandCollapse=False,
                optionItems=option_items,
                sortDisabled=False,
                sortHeader="Tasks"
            )
            
            # Add CardFlow directly to the container
            self.cardflow = self.body_layout.add_cardflow(id="cardflow_container", cardflow_config=cardflow_config)
            
            # Set up event handlers
            try:
                print("Attaching event handlers")
                # Use direct property assignment for all events
                self.cardflow.cardflow.onSort = create_proxy(self.handle_sort)
                self.cardflow.cardflow.onExpand = create_proxy(self.handle_card_expand)
                self.cardflow.cardflow.onCollapse = create_proxy(self.handle_card_collapse)
                self.cardflow.cardflow.onOptions = create_proxy(self.handle_card_options)
                
            except Exception as e_events:
                import traceback
                print(f"Error during event handler setup: {e_events}")
                print(f"Traceback: {traceback.format_exc()}")
        except Exception as e:
            # Display an error message if CardFlow initialization fails
            import traceback
            import sys
            
            # Get detailed exception information
            exc_type = type(e).__name__
            exc_details = str(e)
            tb = traceback.format_exc()
            
            error_message = f"""
            <div style="padding: 20px; color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; margin: 20px;">
                <h3>Error Initializing CardFlow</h3>
                <p><strong>Exception Type:</strong> {exc_type}</p>
                <p><strong>Error Message:</strong> {exc_details}</p>
                <p><strong>Python Version:</strong> {sys.version}</p>
                <details>
                    <summary>Technical Details (Click to expand)</summary>
                    <pre style="background-color: #f8f9fa; padding: 10px; overflow: auto; max-height: 300px;">{tb}</pre>
                </details>
                <p>Please check the console for more details.</p>
            </div>
            """
            self.body_layout.attach_html(id="cardflow_container", html=error_message)
            print(f"CardFlow initialization error: {e}")
            print(f"Traceback: {tb}")

    def handle_toolbar_click(self, id, event):
        """Handle toolbar button clicks."""
        if id == "refresh":
            try:
                self.cardflow.update_header()
                js.alert("CardFlow refreshed!")
            except Exception as e:
                js.alert(f"Error refreshing CardFlow: {str(e)}")
        elif id == "add":
            js.alert("Add card functionality would go here")
        elif id == "help":
            js.alert("CardFlow example help: This demonstrates the DHX CardFlow widget with sample task data.")

    def handle_sort(self, event):
        """Handle sort events in the CardFlow."""
        print(f"CardFlow sorted: {event}")
        js.alert(f"CardFlow sorted: {event}")

    def handle_card_options(self, id, option, event):
        """Handle card option button clicks."""
        print(f"Option clicked: {option} for card {id}")
        js.alert(f"Option clicked: {option} for card {id}")

    def handle_card_expand(self, id, event):
        """Handle card expand events."""
        print(f"Card expanded: {id}")
        try:
            # Get the card data from the config.data array
            data = self.cardflow.cardflow.config.data
            card_data = None
            for i in range(len(data)):
                if data[i].id == id:
                    card_data = data[i]
                    break
            
            if not card_data:
                print(f"Card data not found for id: {id}")
                return
            
            # Create a layout for the expanded content
            layout_config = LayoutConfig(
                type="line",
                rows=[
                    CellConfig(id="details_cell", height="auto"),
                    CellConfig(id="comments_cell", height="auto")
                ]
            )
            
            # Create the layout widget
            content_layout = Layout(config=layout_config)
            
            # Add content to the layout cells
            details_html = f"""
                <div style="padding: 15px; font-family: Arial, sans-serif;">
                    <h3 style="color: #2196F3; margin-bottom: 15px;">Task Details</h3>
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 4px;">
                        <p><strong>Task:</strong> {card_data.task}</p>
                        <p><strong>Assignee:</strong> {card_data.assignee}</p>
                        <p><strong>Priority:</strong> <span style="color: {self.get_priority_color(card_data.priority)}">{card_data.priority}</span></p>
                        <p><strong>Status:</strong> {card_data.status}</p>
                        <p><strong>Deadline:</strong> {card_data.deadline}</p>
                    </div>
                </div>
            """
            
            comments_html = f"""
                <div style="padding: 15px; font-family: Arial, sans-serif;">
                    <h3 style="color: #2196F3; margin-bottom: 15px;">Comments</h3>
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 4px;">
                        <p>{card_data.comments}</p>
                    </div>
                    <div style="margin-top: 15px;">
                        <button onclick="alert('Add comment')" 
                                style="background: #4CAF50; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; margin-right: 10px;">
                            Add Comment
                        </button>
                        <button onclick="alert('Edit task')" 
                                style="background: #2196F3; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer;">
                            Edit Task
                        </button>
                    </div>
                </div>
            """
            
            content_layout.attach_html(id="details_cell", html=details_html)
            content_layout.attach_html(id="comments_cell", html=comments_html)
            
            # Attach the layout widget to the card
            self.cardflow.attach_to_card_content(id, content_layout.layout)
            
        except Exception as e:
            print(f"Error in handle_card_expand: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

    def get_priority_color(self, priority):
        """Helper function to get color based on priority."""
        colors = {
            "Critical": "#f44336",  # Red
            "High": "#ff9800",      # Orange
            "Medium": "#2196F3",    # Blue
            "Low": "#4CAF50"        # Green
        }
        return colors.get(priority, "#757575")  # Default gray

    def handle_card_collapse(self, id, event):
        """Handle card collapse events."""
        print(f"Card collapsed: {id}")
        try:
            # Detach the content using the Python wrapper method
            self.cardflow.detach_from_card_content(id)
            
        except Exception as e:
            print(f"Error in handle_card_collapse: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service() 
