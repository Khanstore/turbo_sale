
from odoo import models, api, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_cash_on_delivery = fields.Boolean('Cash on Delivery')
    cod_amount = fields.Float('Cash on Delivery Amount', help="Amount to be collected on delivery.")

    # This field will be True if all pickings and invoices are finished
    is_order_completed = fields.Boolean(compute='_compute_is_order_completed', store=False)

    @api.depends('picking_ids.state', 'invoice_ids.state')
    def _compute_is_order_completed(self):
        for order in self:
            # Check if there are related records
            has_pickings = bool(order.picking_ids)
            has_invoices = bool(order.invoice_ids)

            # Check if all pickings are 'done' or 'cancel'
            all_pickings_done = all(p.state in ['done', 'cancel'] for p in order.picking_ids)

            # Check if all invoices are 'posted' or 'cancel'
            all_invoices_done = all(i.state in ['posted', 'cancel'] for i in order.invoice_ids)

            # Set the field to True only if records exist and are all completed
            order.is_order_completed = has_pickings and has_invoices and all_pickings_done and all_invoices_done
    def action_confirm_all_with_prompts(self):
        for order in self:
            if order.state == 'draft':
                order.action_confirm()

            pickings = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            insufficient_products = []

            for picking in pickings:
                for move in picking.move_ids_without_package:
                    if move.product_id.type == 'consu' and move.product_uom_qty > move.product_id.qty_available:
                        insufficient_products.append(move.product_id.display_name)

                return {
                    'name': 'Insufficient Stock',
                    'type': 'ir.actions.act_window',
                    'res_model': 'force.delivery.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_ids': self.ids,
                        'default_insufficient_products': ', '.join(insufficient_products),
                        'default_picking_id': picking.id,
                        'default_cod_amount': order.amount_total,
                        'default_carrier_id': picking.carrier_id.id,
                    }
                }

            # return self._process_delivery_invoice()

    def _process_delivery_invoice(self):
        for order in self:
            for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                if picking.state == 'confirmed':
                    picking.action_assign()
                if picking.state in ('assigned', 'partially_available'):
                    picking.button_validate()

            invoice = order._create_invoices()
            invoice.action_post()

            return {
                'name': 'Register Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_model': 'account.move',
                    'active_ids': invoice.ids,
                }
            }

    def _force_delivery_and_invoice(self,data=None):
        for order in self:
            for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                if picking.state == 'confirmed':
                    picking.action_assign()
                picking.button_validate()

            if order.invoice_status == 'to invoice':
                invoice = order._create_invoices()

            invoices=order.invoice_ids
            for invoice in invoices:
                if invoice.state != 'posted':
                    invoice.action_post()
            # If COD, you might want to make the payment directly
            if data and data.get("COD"):
                # Here you can implement logic to handle COD payments
                payment=self.env['account.payment'].create({
                    'payment_type': 'inbound',
                    'memo': invoice.name,
                    'invoice_ids': [(4, invoice.id)],
                    'partner_type': 'customer',

                    'partner_id': order.partner_id.id,

                    'amount': data.get("COD Amount", sum(invoices.mapped('amount_total'))),

                    'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                    'journal_id': order.carrier_id.related_journal.id if order.carrier_id and order.carrier_id.related_journal else self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                })
                payment.action_post()

                # 3. Batch Reconcile
                # Get the receivable line from the payment
                pay_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                )

                # Get all receivable lines from all related invoices
                inv_lines = invoices.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
                )

                # Combine and reconcile them all at once
                if pay_lines and inv_lines:
                    (pay_lines + inv_lines).reconcile()

                return payment

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_cash_on_delivery = fields.Boolean('Cash on Delivery', default=False, help="Check if this picking is Cash on Delivery.")
    cod_amount = fields.Float('Cash on Delivery Amount', help="Amount to be collected on delivery.")
    tracking_url_link = fields.Html(string='Tracking Link', compute='_compute_tracking_url_link')

    def _compute_tracking_url_link(self):
        for picking in self:
            if picking.carrier_tracking_ref and picking.carrier_id.tracking_url:
                tracking_url = picking.carrier_id.tracking_url % picking.carrier_tracking_ref
                picking.tracking_url_link = f'<a href="{tracking_url}" target="_blank">{picking.carrier_tracking_ref}</a>'
            else:
                picking.tracking_url_link = picking.carrier_tracking_ref or ''

    def button_validate(self):

        res = super(StockPicking, self).button_validate()
        if self.is_cash_on_delivery:
            self.message_post(body="This picking is confirmed as Cash on Delivery with amount: %s" % self.cod_amount)
        return res

# class CashOnDeliveryWizard(models.TransientModel):
#     _name = 'cash.on.delivery.wizard'
#     _description = 'Cash on Delivery Confirmation'
#
#     is_cash_on_delivery = fields.Boolean('Is this Cash on Delivery?')
#     cod_amount = fields.Boolean('Is this Cash on Delivery?')
#
#     def action_confirm_cod(self):
#         sale_orders = self.env['sale.order'].browse(self.env.context.get('active_ids'))
#         sale_orders.write({'is_cash_on_delivery': self.is_cash_on_delivery})
#         if self.is_cash_on_delivery:
#             # You can send info to carrier here (e.g., update picking, tracking message, etc.)
#             sale_orders.message_post(body="This order is confirmed as Cash on Delivery.")
#
#         return sale_orders._force_delivery_and_invoice(data)
