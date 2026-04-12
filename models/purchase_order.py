
from odoo import models, api, fields

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    # This field will be True if all pickings and invoices are finished
    is_order_completed = fields.Boolean(compute='_compute_is_order_completed', store=False)

    @api.depends('picking_ids.state', 'invoice_ids.state')
    def _compute_is_order_completed(self):
        for order in self:
            # Check if receipts (pickings) and vendor bills (invoices) exist
            has_receipts = bool(order.picking_ids)
            has_bills = bool(order.invoice_ids)

            # In Purchase, receipts are complete when 'done' or 'cancel'
            all_receipts_done = all(p.state in ['done', 'cancel'] for p in order.picking_ids)

            # Vendor bills (account.move) are complete when 'posted' or 'cancel'
            all_bills_done = all(i.state in ['posted', 'cancel'] for i in order.invoice_ids)

            # Logic: True only if both flows have started and reached a final state
            order.is_order_completed = (
                    has_receipts and
                    has_bills and
                    all_receipts_done and
                    all_bills_done
            )

    def action_complete_purchase_process(self):
        for order in self:
            # 1. Confirm the Purchase Order if it's still a draft/RFQ
            if order.state in ['draft', 'sent']:
                order.button_confirm()

            # 2. Process Receipts (Pickings)
            for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                # Set quantities done to match the demand
                if picking.state not in ('done', 'cancel'):
                    # Validate the picking
                    picking.button_validate()

            # 3. Create and Post Vendor Bills
            # Only create if there isn't an active bill or if the policy allows
            if not order.invoice_ids.filtered(lambda i: i.state != 'cancel'):
                action = order.action_create_invoice()
                # The action returns a window action; we extract the move_id
                invoice_id = action.get('res_id') or action.get('context', {}).get('default_move_ids', [])[0]
                bill = self.env['account.move'].browse(invoice_id)

                # Optional: Set a Bill Date (required for posting in many Odoo versions)
                if not bill.invoice_date:
                    bill.invoice_date = fields.Date.today()

                # Post the bill
                bill.action_post()

        return
