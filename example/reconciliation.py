import json
import sys
from dhxpyt.layout import MainWindow, LayoutConfig, CellConfig
from dhxpyt.reconciliation import ReconciliationConfig

from py_ui_data import py_ui_data  

class reconciliation(MainWindow):
    select_all = False
    # def __init__(self):
    #     super().__init__()
    #     self.set_theme("dark")
    #     self.load_ui()

    def load_ui(self):
        # Create a layout for the body (main content area) with a single column
        body_layout_config = LayoutConfig(
            type="line",
            cols=[CellConfig(id="reconciliation", width="100%")],  # Content column
        )

        # Add the body layout to the pre-existing 'mainwindow' cell and capture the layout instance
        self.mw_body_layout = self.add_layout(id="mainwindow", layout_config=body_layout_config)

        self.reconciliation_data = json.loads(py_ui_data().reconciliation_dataset())

        # Reconciliation configuration
        reconciliation_config = ReconciliationConfig(
            data=self.reconciliation_data
        )

        # Attach the grid to the layout
        self.reconciliation = self.mw_body_layout.add_reconciliation(
            id="reconciliation", reconciliation_config=reconciliation_config
        )

        self.reconciliation.update_header()


if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service()
