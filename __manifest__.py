
{
    "name": "Turbo Sale",
    "version": '18.0.1.0.1',
    # last dev 2025-09-05
    "summary": "One-click sales processing with stock and payment prompts.",
    "author": "SM Ashraf",
    "website": "https://www.eagle-erp.com/",
    "category": "Sales",
    "description": """
        Turbo Sale Module
        -----------------
        This module enhances the sales process by allowing users to confirm sales orders with a single click.
        It prompts for stock availability and payment processing, streamlining the workflow for sales teams.
    """,
    "depends": ["sale_management", "stock", "account"],
    "data": [
        "views/sale_order_view.xml",
        "views/force_delivery_wizard_view.xml",
        "security/ir.model.access.csv",
        "views/stock_picking.xml",
        "views/templates.xml",
    ],
    "installable": True,
    "application": True,
    "image": "static/description/banner.jpg",
    "license": "AGPL-3",
}
