"""
Example application demonstrating the DHX CardFlow widget with pytincture.
This example shows a daily book reconciliation interface with income and expense tracking.
"""
import json
import sys
from datetime import datetime

from dhxpyt.layout import MainWindow, LayoutConfig, CellConfig, Layout
from dhxpyt.tabbar import TabbarConfig, TabConfig
from dhxpyt.cardflow import CardFlowConfig, CardFlowColumnConfig
from dhxpyt.form import FormConfig, CheckboxConfig, ButtonConfig as FormButtonConfig
from dhxpyt.message import MessageConfig
from pyodide.ffi import create_proxy
import js

class cardflow_recon(MainWindow):
    def __init__(self):
        super().__init__()
        self.set_theme("material")
        self.load_ui()

    def load_ui(self):
        # Create a layout for the body (main content area)
        body_layout_config = LayoutConfig(
            type="line",
            rows=[
                CellConfig(id="header_cell", height="auto"),
                CellConfig(id="net_total_cell", height="auto"),
                CellConfig(id="panels_cell", height="100%"),
                CellConfig(id="close_section_cell", height="auto")
            ]
        )

        # Add the body layout to the pre-existing 'mainwindow' cell
        self.body_layout = self.add_layout(id="mainwindow", layout_config=body_layout_config)
        
        # Create header layout
        header_layout_config = LayoutConfig(
            type="line",
            rows=[
                CellConfig(id="title_cell", height="auto"),
                CellConfig(id="subtitle_cell", height="auto")
            ]
        )
        header_layout = self.body_layout.add_layout(id="header_cell", layout_config=header_layout_config)
        
        # Add title and subtitle
        header_layout.attach_html(id="title_cell", html="<div style='font-size: 1.8rem; margin-bottom: 0.5rem; color: #0078D4; text-align: center;'>Daily Book Reconciliation</div>")
        header_layout.attach_html(id="subtitle_cell", html="<div style='color: #666; text-align: center; margin-bottom: 1.5rem;'>End-of-Day Closing for Automotive Repair Shop</div>")

        # Create net total layout
        net_total_layout_config = LayoutConfig(
            type="line",
            rows=[
                CellConfig(id="net_total_display", height="auto")
            ]
        )
        net_total_layout = self.body_layout.add_layout(id="net_total_cell", layout_config=net_total_layout_config)
        # Initialize with default HTML content
        net_total_layout.attach_html(id="net_total_display", html="<div style='font-size: 1.5rem; font-weight: 700; text-align: center; padding: 1rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);'>$0</div>")
        # Store the layout for future reference
        self.net_total_layout = net_total_layout

        # Create panels layout
        panels_layout_config = LayoutConfig(
            type="columns",
            cols=[
                CellConfig(id="income_panel", width="50%"),
                CellConfig(id="expense_panel", width="50%")
            ]
        )
        self.panels_layout = self.body_layout.add_layout(id="panels_cell", layout_config=panels_layout_config)

        # Configure CardFlow columns for both panels
        cardflow_columns = [
            CardFlowColumnConfig(id="checkbox", header="", width="50px", dataType="checkbox"),
            CardFlowColumnConfig(id="date", header="Date", width="120px", dataType="date", dataFormat="%Y-%m-%d"),
            CardFlowColumnConfig(id="memo", header="Memo", width="200px"),
            CardFlowColumnConfig(id="amount", header="Amount", width="120px", dataType="number", dataFormat="$#,##0.00")
        ]

        # Sample data for Income panel
        income_data = [
            {
                "id": "income1",
                "category": "Total Sales",
                "date": "2025-01-31",
                "memo": "Sale of Product A",
                "amount": 1000.00,
                "checked": True
            },
            {
                "id": "income2",
                "category": "Total Sales",
                "date": "2025-01-31",
                "memo": "Sale of Product B",
                "amount": 750.00,
                "checked": True
            },
            {
                "id": "income3",
                "category": "Received on Account",
                "date": "2025-01-31",
                "memo": "Payment received",
                "amount": 500.00,
                "checked": True
            }
        ]

        # Sample data for Expense panel
        expense_data = [
            {
                "id": "expense1",
                "category": "Bank Deposits",
                "date": "2025-01-31",
                "memo": "Deposit from sales",
                "amount": 800.00,
                "checked": True
            },
            {
                "id": "expense2",
                "category": "Bank Deposits",
                "date": "2025-01-31",
                "memo": "Additional deposit",
                "amount": 600.00,
                "checked": True
            },
            {
                "id": "expense3",
                "category": "Cash paidouts",
                "date": "2025-01-31",
                "memo": "Payment for services",
                "amount": 500.00,
                "checked": True
            }
        ]

        # Create CardFlow configurations
        income_config = CardFlowConfig(
            columns=cardflow_columns,
            data=income_data,
            editable=True,
            groupable=True,
            group={"order": ["category"]},
            hideExpandCollapse=False,
            sortDisabled=True,
            sortHeader="Income: $0.00"
        )

        expense_config = CardFlowConfig(
            columns=cardflow_columns,
            data=expense_data,
            editable=True,
            groupable=True,
            group={"order": ["category"]},
            hideExpandCollapse=False,
            sortDisabled=True,
            sortHeader="Expenses: $0.00"
        )

        try:
            # Add CardFlows to panels
            self.income_cardflow = self.panels_layout.add_cardflow(id="income_panel", cardflow_config=income_config)
            self.expense_cardflow = self.panels_layout.add_cardflow(id="expense_panel", cardflow_config=expense_config)
            
            # Set up event handlers
            self.income_cardflow.cardflow.onChange = create_proxy(self.handle_card_change)
            self.expense_cardflow.cardflow.onChange = create_proxy(self.handle_card_change)
            
        except Exception as e:
            import traceback
            print(f"Error initializing CardFlows: {e}")
            print(f"Traceback: {traceback.format_exc()}")

        # Create close books form
        close_form_config = FormConfig(
            rows=[
                {
                    "id": "override_row",
                    "cols": [
                        CheckboxConfig(
                            id="overrideCheckbox",
                            label="I understand the imbalance and want to close the books anyway.",
                            hidden=True
                        )
                    ]
                },
                {
                    "id": "button_row",
                    "cols": [
                        FormButtonConfig(
                            id="closeBooksBtn",
                            text="Close Books",
                            disabled=True
                        )
                    ]
                }
            ],
            css="text-align: center; margin-top: 2rem;"
        )
        self.close_form = self.body_layout.add_form(id="close_section_cell", form_config=close_form_config)
        self.close_form.on_change(create_proxy(self.handle_override_change))
        self.close_form.on_click(create_proxy(self.handle_close_books))

        # Initial calculation
        self.recalc_totals()

    def handle_card_change(self, event):
        """Handle changes to any card in either CardFlow."""
        self.recalc_totals()

    def handle_override_change(self, event):
        """Handle changes to the override checkbox."""
        self.recalc_totals()

    def handle_close_books(self, event):
        """Handle closing the books."""
        if event.id == "closeBooksBtn":
            # Disable all checkboxes and the close button
            self.income_cardflow.cardflow.config.editable = False
            self.expense_cardflow.cardflow.config.editable = False
            self.close_form.form.setValue({
                "overrideCheckbox": False
            })
            self.close_form.form.config.disabled = True
            self.show_message("Books closed. The day's transactions are now locked.", "success")

    def show_message(self, text, type="info"):
        """Show a message using the DHX message component."""
        message_config = MessageConfig(
            text=text,
            type=type,
            expire=3000
        )
        self.add_message(message_config)

    def recalc_totals(self):
        """Recalculate all totals and update the UI."""
        # Get all data from both CardFlows and convert to Python lists
        income_data = list(self.income_cardflow.cardflow.config.data)
        expense_data = list(self.expense_cardflow.cardflow.config.data)

        # Calculate totals
        total_income = 0
        for item in income_data:
            if not hasattr(item, "checked") or item.checked:
                total_income += item.amount

        total_expenses = 0
        for item in expense_data:
            if not hasattr(item, "checked") or item.checked:
                total_expenses += item.amount

        net_total = total_income - total_expenses

        # Update panel headers with totals
        self.income_cardflow.cardflow.config.sortHeader = f"Income: ${total_income:,.2f}"
        self.expense_cardflow.cardflow.config.sortHeader = f"Expenses: ${total_expenses:,.2f}"

        # Update net total display
        html_content = f"<div style='font-size: 1.5rem; font-weight: 700; text-align: center; padding: 1rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);'>${net_total:,.2f}</div>"
        
        # Update net total styling
        if net_total == 0:
            html_content = f"<div style='font-size: 1.5rem; font-weight: 700; text-align: center; padding: 1rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1); color: #28a745; background-color: #e6f9e6;'>${net_total:,.2f}</div>"
            # Hide the override checkbox and disable the button
            self.close_form.form.setValue({
                "overrideCheckbox": False
            })
            self.close_form.form.config.hidden = True
            self.close_form.form.config.disabled = True
        else:
            html_content = f"<div style='font-size: 1.5rem; font-weight: 700; text-align: center; padding: 1rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1); color: #dc3545; background-color: #f9e6e6;'>${net_total:,.2f}</div>"
            # Show the form and update button state
            self.close_form.form.config.hidden = False
            override_checked = self.close_form.form.getValue("overrideCheckbox")
            if override_checked:
                self.close_form.form.config.disabled = False
            else:
                self.close_form.form.config.disabled = True
            
        # Set the updated HTML content
        self.net_total_layout.attach_html(id="net_total_display", html=html_content)

if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service() 
