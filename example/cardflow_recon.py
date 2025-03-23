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
            # Total Sales transactions
            {
                "id": "income_trans1",
                "subcategory": "Total Sales",
                "date": "2025-01-31",
                "memo": "Sale of Product A",
                "amount": 1000.00,
                "checked": True
            },
            {
                "id": "income_trans2",
                "subcategory": "Total Sales",
                "date": "2025-01-31",
                "memo": "Sale of Product B",
                "amount": 750.00,
                "checked": True
            },
            
            # Received on Account transactions
            {
                "id": "income_trans3",
                "subcategory": "Received on Account",
                "date": "2025-01-31",
                "memo": "Payment received",
                "amount": 500.00,
                "checked": True
            },
            
            # Cash on hand (start) transactions
            {
                "id": "income_trans4",
                "subcategory": "Cash on hand (start)",
                "date": "2025-01-31",
                "memo": "Opening balance",
                "amount": 200.00,
                "checked": True
            },
            
            # Manual Accounts Receivable transactions
            {
                "id": "income_trans5",
                "subcategory": "Manual Accounts Receivable",
                "date": "2025-01-31",
                "memo": "Adjustment entry",
                "amount": 50.00,
                "checked": True
            },
            {
                "id": "income_trans6",
                "subcategory": "Manual Accounts Receivable",
                "date": "2025-01-31",
                "memo": "Manual AR adjustment",
                "amount": 75.00,
                "checked": True
            }
        ]

        # Sample data for Expense panel
        expense_data = [
            # Bank Deposits transactions
            {
                "id": "expense_trans1",
                "subcategory": "Bank Deposits",
                "date": "2025-01-31",
                "memo": "Deposit from sales",
                "amount": 800.00,
                "checked": True
            },
            {
                "id": "expense_trans2",
                "subcategory": "Bank Deposits",
                "date": "2025-01-31",
                "memo": "Additional deposit",
                "amount": 600.00,
                "checked": True
            },
            
            # Cash paidouts transactions
            {
                "id": "expense_trans3",
                "subcategory": "Cash paidouts",
                "date": "2025-01-31",
                "memo": "Payment for services",
                "amount": 500.00,
                "checked": True
            },
            {
                "id": "expense_trans4",
                "subcategory": "Cash paidouts",
                "date": "2025-01-31",
                "memo": "Payment for supplies",
                "amount": 300.00,
                "checked": True
            },
            
            # Cash on hand (end) transactions
            {
                "id": "expense_trans5",
                "subcategory": "Cash on hand (end)",
                "date": "2025-01-31",
                "memo": "Closing balance",
                "amount": 150.00,
                "checked": True
            },
            
            # Applied Prepayments transactions
            {
                "id": "expense_trans6",
                "subcategory": "Applied Prepayments",
                "date": "2025-01-31",
                "memo": "Prepayment applied",
                "amount": 200.00,
                "checked": True
            }
        ]

        # Create CardFlow configurations
        income_config = CardFlowConfig(
            columns=cardflow_columns,
            data=income_data,
            editable=True,
            groupable=True,
            group={"order": ["subcategory"]},
            hideExpandCollapse=False,
            sortDisabled=False,
            sortHeader="Income: $0.00"
        )

        expense_config = CardFlowConfig(
            columns=cardflow_columns,
            data=expense_data,
            editable=True,
            groupable=True,
            group={"order": ["subcategory"]},
            hideExpandCollapse=False,
            sortDisabled=False,
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
        # Check if this is a checkbox change event
        if hasattr(event, "column") and event.column == "checkbox":
            # Update the data item's checked status in the CardFlow data
            if hasattr(event, "value") and hasattr(event, "id"):
                # Find the item in the data and update it
                cardflow_id = event.target.id if hasattr(event, "target") and hasattr(event.target, "id") else None
                
                if cardflow_id == "income_panel":
                    data = self.income_cardflow.cardflow.config.data
                    # Find and update the changed item
                    for item in data:
                        if item.id == event.id:
                            item.checked = event.value
                            break
                elif cardflow_id == "expense_panel":
                    data = self.expense_cardflow.cardflow.config.data
                    # Find and update the changed item
                    for item in data:
                        if item.id == event.id:
                            item.checked = event.value
                            break
        
        # Recalculate totals
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
        total_expenses = 0
        
        # Keep track of subcategory totals
        income_subcategories = {}
        expense_subcategories = {}
        
        # Process income transactions and calculate subcategory totals
        for item in income_data:
            subcategory = item.subcategory if hasattr(item, "subcategory") else "Uncategorized"
            is_checked = item.checked if hasattr(item, "checked") else True
            
            # Initialize subcategory if not exists
            if subcategory not in income_subcategories:
                income_subcategories[subcategory] = 0
            
            # Add amount to subcategory total if checked
            if is_checked:
                amount = item.amount if hasattr(item, "amount") else 0
                income_subcategories[subcategory] += amount
                total_income += amount
        
        # Process expense transactions and calculate subcategory totals
        for item in expense_data:
            subcategory = item.subcategory if hasattr(item, "subcategory") else "Uncategorized"
            is_checked = item.checked if hasattr(item, "checked") else True
            
            # Initialize subcategory if not exists
            if subcategory not in expense_subcategories:
                expense_subcategories[subcategory] = 0
            
            # Add amount to subcategory total if checked
            if is_checked:
                amount = item.amount if hasattr(item, "amount") else 0
                expense_subcategories[subcategory] += amount
                total_expenses += amount
        
        # Calculate net total
        net_total = total_income - total_expenses

        # Update panel headers with totals
        self.income_cardflow.cardflow.config.sortHeader = f"Income: ${total_income:,.2f}"
        self.expense_cardflow.cardflow.config.sortHeader = f"Expenses: ${total_expenses:,.2f}"

        # Update net total display
        if net_total == 0:
            html_content = f"<div style='font-size: 1.5rem; font-weight: 700; text-align: center; padding: 1rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1); color: #28a745; background-color: #e6f9e6;'>${net_total:,.2f}</div>"
            # Hide the override checkbox and enable the close button
            self.close_form.form.setValue({
                "overrideCheckbox": False
            })
            # Hide the override checkbox and enable the button
            checkbox_item = self.close_form.form.getItem("overrideCheckbox")
            if checkbox_item:
                checkbox_item.hide()
                
            button_item = self.close_form.form.getItem("closeBooksBtn")
            if button_item:
                button_item.enable()
        else:
            html_content = f"<div style='font-size: 1.5rem; font-weight: 700; text-align: center; padding: 1rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1); color: #dc3545; background-color: #f9e6e6;'>${net_total:,.2f}</div>"
            # Show the override checkbox and update button state
            checkbox_item = self.close_form.form.getItem("overrideCheckbox")
            if checkbox_item:
                checkbox_item.show()
                
            override_checked = self.close_form.form.getValue("overrideCheckbox")
            button_item = self.close_form.form.getItem("closeBooksBtn")
            if button_item:
                if override_checked:
                    button_item.enable()
                else:
                    button_item.disable()
            
        # Set the updated HTML content
        self.net_total_layout.attach_html(id="net_total_display", html=html_content)

if __name__ == "__main__" and sys.platform != "emscripten":
    from pytincture import launch_service
    launch_service() 
