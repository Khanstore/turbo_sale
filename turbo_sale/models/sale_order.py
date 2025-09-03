
from odoo import models, api, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_cash_on_delivery = fields.Boolean('Cash on Delivery')
    cod_amount = fields.Float('Cash on Delivery Amount', help="Amount to be collected on delivery.")

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

            invoice = order._create_invoices()
            invoice.action_post()
            # return invoice.action_register_payment()
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
