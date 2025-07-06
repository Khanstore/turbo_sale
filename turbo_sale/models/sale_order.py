
from odoo import models, api, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

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

            if insufficient_products:
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
                    }
                }

            return self._process_delivery_invoice()

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

    def _force_delivery_and_invoice(self):
        for order in self:
            for picking in order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                if picking.state == 'confirmed':
                    picking.action_assign()
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
