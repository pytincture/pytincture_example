import json
import sys
from dhxpyt.layout import MainWindow
from dhxpyt.grid import GridConfig, GridColumnConfig  # Grid and GridColumnConfig
from dhxpyt.layout import LayoutConfig, CellConfig

from py_ui_data import py_ui_data  # Assuming this is pulling the book data

class grid(MainWindow):
    select_all = False
    def __init__(self):
        super().__init__()
        self.set_theme("dark")
        self.load_ui()

    def load_ui(self):
        # Create a layout for the body (main content area) with a single column
        body_layout_config = LayoutConfig(
            type="line",
            cols=[
                CellConfig(id="mainwindow_content", width="100%")  # Content column
            ]
        )

        # Add the body layout to the pre-existing 'mainwindow' cell and capture the layout instance
        self.mw_body_layout = self.add_layout(id="mainwindow", layout_config=body_layout_config)

        # Grid columns configuration using GridColumnConfig
        grid_columns = [
            GridColumnConfig(
                width="50",
                id="selected",
                editable=True,
                type="boolean",
                sortable=False,
                header=[
                    {
                        "text": """
                        <label class="dhx_checkbox dhx_cell-editor__checkbox ">
                            <input type="checkbox" class="dhx_checkbox__input dhx_checkbox--check-all">
                            <span class="dhx_checkbox__visual-input "></span>
                        </label>
                    """
                    }
                ],
            ),
            GridColumnConfig(width=1000, id="title", header=[{"text": "Title"}]),
            # GridColumnConfig(width=200, id="column3", header=[{"text": "Column 3"}]),
            # GridColumnConfig(width=200, id="column4", header=[{"text": "Column 4"}]),
            # GridColumnConfig(width=200, id="column5", header=[{"text": "Column 5"}])
        ]

        self.grid_data = json.loads(py_ui_data().dataset())
        for item in self.grid_data:
            item["selected"] = False

        # Grid configuration with columns
        grid_config = GridConfig(
            multiselection=True,
            columns=grid_columns,
            data=self.grid_data
        )

        # Attach the grid to the layout
        self.grid = self.mw_body_layout.add_grid(id="mainwindow_content", grid_config=grid_config)

        self.grid.on_cell_click(self.handle_grid_click)

        # self.grid.add_event_handler("afterSelect", self.handle_grid_select)
        # self.grid.add_event_handler("afterUnSelect", self.handle_grid_unselect)
        # self.grid.add_event_handler("headerCellClick", self.handle_header_click)

    def handle_grid_select(self, row, column):
        row.selected = True

    def handle_grid_unselect(self, row, column):
        row.selected = False

    def handle_grid_click(self, row, column, event):
        print(row)
        print(row["selected"])
        # row["selected"] = not row["selected"]
        print(row["selected"])
        # row["title"] = "Hello"

        print(row.update(row))
        print(row)
        print(row["id"])

        print(dir(self.grid))
        # self.grid.update_cell(row["id"], row)
        # self.grid.update_row(
        #     row["id"], json.dumps({"selected": True, "title": "Hello"})
        # )
        # self.grid.grid.data.update(json.dumps([{"selected": True, "title": "Hello"}]))


if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service()
