
from odoo import models, fields,api

class ForceDeliveryWizard(models.TransientModel):
    _name = 'force.delivery.wizard'
    _description = 'Force Delivery Wizard'
    is_cash_on_delivery = fields.Boolean('Is this Cash on Delivery?', default=False, help="Check if the delivery is cash on delivery.")
    cod_amount = fields.Float('Cash on Delivery Amount', help="Amount to be collected on delivery.")
    add_charge=fields.Boolean('Add Charge', help="Check if you want to add a charge for cash on delivery.")
    insufficient_products = fields.Text('Insufficient Stock Products', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking',  help="Select the picking to force delivery.")
    carrier_id= fields.Many2one('delivery.carrier', string='Carrier', help="Select the delivery carrier for this picking.")

    @api.onchange('is_cash_on_delivery')
    def _onchange_is_cash_on_delivery(self):
        if self.is_cash_on_delivery:
            # picking_id থেকে cod_amount আনুন অথবা নিজস্ব logic দিন
            self.cod_amount = self._context['default_cod_amount']
        else:
            self.cod_amount = 0

        self.picking_id.cod_amount= self.cod_amount
        self.picking_id.is_cash_on_delivery= self.is_cash_on_delivery


    def action_confirm(self):
        picking = self.picking_id
        picking.is_cash_on_delivery = self.is_cash_on_delivery
        picking.cod_amount = self.cod_amount if self.is_cash_on_delivery else 0.0
        picking.carrier_id = self.carrier_id

        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.button_validate()
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_ids'))
        payment=sale_order._force_delivery_and_invoice({"COD":self.is_cash_on_delivery, "COD Amount":self.cod_amount if self.is_cash_on_delivery else 0.0})

        if payment :
            return {
                'name': 'Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': payment.id,  # <--- existing record
                'target': 'current',
            }
        else:
            return {
                'name': 'Register Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_model': 'account.move',
                    'active_ids': sale_order.invoice_ids.id,
                    'default_journal_id': self.carrier_id.related_journal.id,

                }
            }

        # return {
        #     'name': 'Cash on Delivery?',
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'cash.on.delivery.wizard',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {'active_ids': self.env.context.get('active_ids')},
        # }
